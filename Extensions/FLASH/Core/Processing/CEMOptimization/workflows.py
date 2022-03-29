from typing import Tuple

import numpy as np

from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.roiContour import ROIContour
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing import crop3D
from Core.Processing.ImageProcessing.imageTransform3D import ImageTransform3D
from Core.event import Event
from Extensions.FLASH.Core.Data.cem import BiComponentCEM
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam
from Extensions.FLASH.Core.Processing.CEMOptimization import cemObjectives
from Extensions.FLASH.Core.Processing.CEMOptimization.cemOptimizer import CEMOptimizer, CEMDoseCalculator


class SingleBeamCEMOptimizationWorkflow():
    def __init__(self):
        self.ctCalibration = None
        self.beamModel = None
        self.targetROI = None
        self.gantryAngle = 0
        self.cemToIsocenter = 100
        self.beamEnergy = 226
        self.ct = None
        self.targetDose = None
        self.spotSpacing = 5.
        self.rangeShifterRSP = 1.
        self.cemRSP = 1.

        self.doseUpdateEvent = Event(object)
        self.planUpdateEvent = Event(RTPlan)
        self.fValEvent = Event(Tuple)

        self.cemOptimizer = CEMOptimizer()
        self.cemOptimizer.doseUpdateEvent.connect(self.doseUpdateEvent.emit)
        self.cemOptimizer.planUpdateEvent.connect(self.planUpdateEvent.emit)
        self.cemOptimizer.fValEvent.connect(self.fValEvent.emit)

    def run(self) -> RTPlan:
        if isinstance(self.targetROI, ROIContour):
            self.targetROI = self.targetROI.getBinaryMask(self.ct.origin, self.ct.gridSize, self.ct.spacing)

        patient = self.ct.patient

        plan = self._initializePlan()
        beam = plan.beam

        # Pad CT
        self._prepareCTAndROI(plan)
        self.ct.name = 'CT with CEM'
        self.ct.patient = patient
        self.targetROI.patient = patient

        # Initialize CEM
        cem = BiComponentCEM.fromBeam(self.ct, beam)
        cem.cemRSP = self.cemRSP
        cem.rangeShifterRSP = self.rangeShifterRSP
        beam.cem = cem

        # Optimize CEM and plan
        plan = self._configureAndRunCEMOpti(self.ct, plan, targetROI)
        self.planUpdateEvent.emit(plan)

        # Final dose
        doseImage = self._computeFinalDose(self.ct, plan)
        doseImage.patient = patient
        doseImage.name = 'Final dose'
        self.doseUpdateEvent.emit(doseImage)

        return plan

    def _prepareCTAndROI(self, plan):
        beam = plan.beams[0]

        # Pad CT and targetROI so that both can fully contain the CEM
        ctBEV = ImageTransform3D.dicomToIECGantry(self.ct, beam, fillValue=-1024.)
        targetROIBEV = ImageTransform3D.dicomToIECGantry(self.targetROI, beam, fillValue=-0.)

        padLength = int(150. / ctBEV.spacing[2])
        newOrigin = np.array(ctBEV.origin)
        newOrigin[2] = newOrigin[2] - padLength * ctBEV.spacing[2]
        newArray = -1000 * np.ones((ctBEV.gridSize[0], ctBEV.gridSize[1], ctBEV.gridSize[
            2] + padLength))  # We choose -1000 and not -1024 because we will crop evrthng > -1000
        newArray[:, :, padLength:] = ctBEV.imageArray
        ctBEV.imageArray = newArray
        ctBEV.origin = newOrigin

        newArray = np.zeros((targetROIBEV.gridSize[0], targetROIBEV.gridSize[1], targetROIBEV.gridSize[2] + padLength))
        newArray[:, :, padLength:] = targetROIBEV.imageArray
        targetROIBEV.imageArray = newArray
        targetROIBEV.origin = newOrigin

        ct = ImageTransform3D.iecGantryToDicom(ctBEV, beam, fillValue=-1024.)
        targetROI = ImageTransform3D.iecGantryToDicom(targetROIBEV, beam, fillValue=0)

        boundingBox = crop3D.getBoxAboveThreshold(ct, -1023)

        crop3D.crop3DDataAroundBox(ct, boundingBox, [2, 2, 2])
        crop3D.crop3DDataAroundBox(targetROI, boundingBox, [2, 2, 2])

        self.ct = ct
        self.targetROI = targetROI

    def _initializePlan(self) -> RTPlan:
        plan = RTPlan()
        beam = CEMBeam()
        beam.isocenterPosition = self.targetROI.centerOfMass
        beam.gantryAngle = self.gantryAngle
        beam.cemToIsocenter = self.cemToIsocenter  # Distance between CEM and isocenter
        layer = PlanIonLayer(nominalEnergy=self.beamEnergy)
        beam.appendLayer(layer)
        plan.appendBeam(beam)

        return plan

    def _configureAndRunCEMOpti(self, ct:CTImage, plan:RTPlan, targetROI:ROIMask) -> RTPlan:
        # OARs are defined around the TV
        oarAndTVROI = ROIMask.fromImage3D(targetROI)
        oarAndTVROI.dilate(10)

        oarROI = ROIMask.fromImage3D(targetROI)
        oarROI.imageArray = np.logical_xor(oarAndTVROI.imageArray.astype(bool), targetROI.imageArray.astype(bool))

        # This is a dose calculator that will cache results and only recompute them if CEM or plan has changed
        print('Initializing dose calculator...')
        doseCalculator = CEMDoseCalculator()
        doseCalculator.beamModel = self.beamModel
        doseCalculator.nbPrimaries = 5e4
        doseCalculator.ctCalibration = self.ctCalibration
        doseCalculator.plan = plan
        doseCalculator.roi = oarAndTVROI
        doseCalculator.ct = ct

        # These are our objectives
        print('Initializing objectives...')
        objectifMin = cemObjectives.DoseMinObjective(targetROI, self.targetDose, doseCalculator)
        objectifMin.beamModel = self.beamModel
        objectifMax = cemObjectives.DoseMaxObjective(targetROI, self.targetDose + 0.2, doseCalculator)
        objectifMax.beamModel = self.beamModel
        objectifMax2 = cemObjectives.DoseMaxObjective(oarROI, self.targetDose / 2., doseCalculator)
        objectifMax2.beamModel = self.beamModel

        # A single optimizer for both plan an CEM
        print('Initializing optimizer...')
        self.cemOptimizer.maxIterations = 25
        self.cemOptimizer.spotSpacing = self.spotSpacing
        self.cemOptimizer.targetMask = targetROI
        self.cemOptimizer.absTol = self.targetDose / 50.
        self.cemOptimizer.ctCalibration = self.ctCalibration

        self.cemOptimizer.appendObjective(objectifMin, weight=1.)
        self.cemOptimizer.appendObjective(objectifMax, weight=1.)
        self.cemOptimizer.appendObjective(objectifMax2, weight=0.5)

        # Let's optimize the plan and the CEM!
        print('Starting optimization...')
        self.cemOptimizer.run(plan, ct)

        return plan

    def _computeFinalDose(self, ct:CTImage, plan:RTPlan) -> DoseImage:
        # Update CT with CEM
        beam = plan.beams[0]
        cem = beam.cem

        [rsROI, cemROI] = beam.cem.computeROIs(self.ct, beam)

        ctArray = ct.imageArray
        ctArray[cemROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.cemRSP, energy=100.)
        ctArray[rsROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.rangeShifterRSP, energy=100.)

        ct.imageArray = ctArray

        # Final dose computation
        doseCalculator = MCsquareDoseCalculator()
        doseCalculator.beamModel = self.beamModel
        doseCalculator.nbPrimaries = 2e7
        doseCalculator.ctCalibration = self.ctCalibration

        doseImage = doseCalculator.computeDose(ct, plan)

        return doseImage
    