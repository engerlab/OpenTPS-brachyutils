from typing import Tuple, Sequence

import numpy as np

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.roiContour import ROIContour
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing import crop3D
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Core.event import Event
from Extensions.FLASH.Core.Data.cem import BiComponentCEM
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam
from Extensions.FLASH.Core.Processing.CEMOptimization import cemObjectives
from Extensions.FLASH.Core.Processing.CEMOptimization.cemOptimizer import CEMOptimizer, CEMDoseCalculator
from Extensions.FLASH.Core.Processing.RangeEnergy import energyToRange


class Objective:
    def __init__(self, objectiveTerm=None, weight=1.):
        self.weight = weight
        self.objectiveTerm:cemObjectives.CEMAbstractDoseFidelityTerm = objectiveTerm

class SingleBeamCEMOptimizationWorkflow():
    def __init__(self):
        self.ctCalibration = None
        self.beamModel = None
        self.gantryAngle = 0
        self.cemToIsocenter = 100
        self.beamEnergy = 226
        self.ct = None
        self.objectives:Sequence[Objective] = []
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

        self._targetROI = None
        self._globalROI = None

    def run(self) -> RTPlan:
        patient = self.ct.patient

        self._setTargetROI()

        self._plan = self._initializePlan()
        beam = self._plan.beams[0]

        # Pad CT
        self._prepareCTAndROIs()
        self.ct.name = 'CT with CEM'
        self.ct.patient = patient

        # Initialize CEM
        cem = BiComponentCEM.fromBeam(self.ct, beam)
        cem.cemRSP = self.cemRSP
        cem.rangeShifterRSP = self.rangeShifterRSP
        beam.cem = cem

        # Optimize CEM and plan
        self._configureAndRunCEMOpti()
        self.planUpdateEvent.emit(self._plan)

        # Final dose
        doseImage = self._computeFinalDose()
        doseImage.patient = patient
        doseImage.name = 'Final dose'
        self.doseUpdateEvent.emit(doseImage)

        return self._plan

    def _setTargetROI(self):
        targetROIVal = []

        for objective in self.objectives:
            obj = objective.objectiveTerm
            roi = obj.roi

            if isinstance(roi, ROIContour):
                roi = roi.getBinaryMask(self.ct.origin, self.ct.gridSize, self.ct.spacing)
            else:
                roi = imageTransform3D.intersect(roi, self.ct, inPlace=False, fillValue=0)

            if isinstance(obj, cemObjectives.DoseMinObjective):
                if not len(targetROIVal):
                    targetROIVal = roi.imageArray.astype(bool)
                else:
                    targetROIVal = np.logical_or(targetROIVal.astype(bool), roi.imageArray.astype(bool))

        self._targetROI = ROIMask.fromImage3D(self.ct)
        self._targetROI.imageArray = targetROIVal


    def _prepareCTAndROIs(self):
        beam = self._plan.beams[0]

        # Pad CT and targetROI so that both can fully contain the CEM
        ctBEV = imageTransform3D.dicomToIECGantry(self.ct, beam, fillValue=-1024.)

        padLength = int(self._padLength() / ctBEV.spacing[2])
        newOrigin = np.array(ctBEV.origin)
        newOrigin[2] = newOrigin[2] - padLength * ctBEV.spacing[2]
        newArray = -1000 * np.ones((ctBEV.gridSize[0], ctBEV.gridSize[1], ctBEV.gridSize[2] + padLength))  # We choose -1000 and not -1024 because we will crop evrthng > -1000
        newArray[:, :, padLength:] = ctBEV.imageArray
        ctBEV.imageArray = newArray
        ctBEV.origin = newOrigin

        ct = imageTransform3D.iecGantryToDicom(ctBEV, beam, fillValue=-1024.)

        boundingBox = crop3D.getBoxAboveThreshold(ct, -1023)

        crop3D.crop3DDataAroundBox(ct, boundingBox, [2, 2, 2])

        globalROIVal = []
        targetROIVal = []
        for objective in self.objectives:
            obj = objective.objectiveTerm
            roi = obj.roi

            if isinstance(roi, ROIContour):
                roi = roi.getBinaryMask(self.ct.origin, self.ct.gridSize, self.ct.spacing)
            else:
                roi = imageTransform3D.intersect(roi, self.ct, inPlace=False, fillValue=0)

            targetROIBEV = imageTransform3D.dicomToIECGantry(roi, beam, fillValue=-0.)
            newArray = np.zeros((targetROIBEV.gridSize[0], targetROIBEV.gridSize[1], targetROIBEV.gridSize[2] + padLength))
            newArray[:, :, padLength:] = targetROIBEV.imageArray
            targetROIBEV.imageArray = newArray
            targetROIBEV.origin = newOrigin

            roi = imageTransform3D.iecGantryToDicom(targetROIBEV, beam, fillValue=0)
            crop3D.crop3DDataAroundBox(roi, boundingBox, [2, 2, 2])

            obj.roi = roi

            if isinstance(obj, cemObjectives.DoseMinObjective):
                if not len(targetROIVal):
                    targetROIVal = roi.imageArray.astype(bool)
                else:
                    targetROIVal = np.logical_or(targetROIVal.astype(bool), roi.imageArray.astype(bool))

            if not len(globalROIVal):
                globalROIVal = roi.imageArray.astype(bool)
            else:
                globalROIVal = np.logical_or(globalROIVal.astype(bool), roi.imageArray.astype(bool))

        self.ct = ct

        self._targetROI = ROIMask.fromImage3D(self.ct)
        self._targetROI.imageArray = targetROIVal

        self._globalROI = ROIMask.fromImage3D(self.ct)
        self._globalROI.imageArray = globalROIVal

    def _padLength(self) -> float:
        cemThicknessGuess = 50 # Arbitrarily set right now.

        padLength = cemThicknessGuess/self.cemRSP + energyToRange(self.beamEnergy)/self.rangeShifterRSP

        return padLength


    def _initializePlan(self) -> RTPlan:
        plan = RTPlan()
        beam = CEMBeam()
        beam.isocenterPosition = self._targetROI.centerOfMass
        beam.gantryAngle = self.gantryAngle
        beam.cemToIsocenter = self.cemToIsocenter  # Distance between CEM and isocenter
        layer = PlanIonLayer(nominalEnergy=self.beamEnergy)
        beam.appendLayer(layer)
        plan.appendBeam(beam)

        return plan

    def _configureAndRunCEMOpti(self):
        plan = self._plan
        ct = self.ct

        # This is a dose calculator that will cache results and only recompute them if CEM or plan has changed
        print('Initializing dose calculator...')
        doseCalculator = CEMDoseCalculator()
        doseCalculator.beamModel = self.beamModel
        doseCalculator.nbPrimaries = 5e4
        doseCalculator.ctCalibration = self.ctCalibration
        doseCalculator.plan = plan
        doseCalculator.roi = self._globalROI
        doseCalculator.ct = ct

        # A single optimizer for both plan an CEM
        print('Initializing optimizer...')
        self.cemOptimizer.maxIterations = 25
        self.cemOptimizer.spotSpacing = self.spotSpacing
        self.cemOptimizer.targetMask = self._targetROI
        self.cemOptimizer.absTol = 1.
        self.cemOptimizer.ctCalibration = self.ctCalibration

        for objective in self.objectives:
            obj = objective.objectiveTerm
            obj.doseCalculator = doseCalculator
            obj.beamModel = self.beamModel
            self.cemOptimizer.appendObjective(obj, weight=objective.weight)

        # Let's optimize the plan and the CEM!
        print('Starting optimization...')
        self.cemOptimizer.run(plan, ct)

    def _computeFinalDose(self) -> DoseImage:
        ct = self.ct
        plan = self._plan

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
