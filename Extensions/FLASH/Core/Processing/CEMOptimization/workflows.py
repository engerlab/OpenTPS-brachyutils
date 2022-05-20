from typing import Tuple, Sequence

import numpy as np

from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.roiContour import ROIContour
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Core.event import Event
from Extensions.FLASH.Core.Data.aperture import Aperture
from Extensions.FLASH.Core.Data.cem import BiComponentCEM
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam
from Extensions.FLASH.Core.Processing.CEMOptimization import cemObjectives
from Extensions.FLASH.Core.Processing.CEMOptimization.cemDoseCalculator import CEMDoseCalculator
from Extensions.FLASH.Core.Processing.CEMOptimization.cemOptimizer import CEMOptimizer
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
        self.apertureToIsocenter = 100
        self.beamEnergy = 226
        self.ct = None
        self.objectives:Sequence[Objective] = []
        self.spotSpacing = 5.
        self.rangeShifterRSP = 1.
        self.cemRSP = 1.
        self.apertureRSP = 8.73
        self.bodyROI = None

        self.doseUpdateEvent = Event(object)
        self.planUpdateEvent = Event(RTPlan)
        self.fValEvent = Event(Tuple)

        self.cemOptimizer = CEMOptimizer()
        self.cemOptimizer.doseUpdateEvent.connect(self.doseUpdateEvent.emit)
        self.cemOptimizer.planUpdateEvent.connect(self.planUpdateEvent.emit)
        self.cemOptimizer.fValEvent.connect(self.fValEvent.emit)

        self._plan = None
        self._targetROI = None
        self._globalROI = None
        self._finalDose = None
        self._ctWithCEM = None
        self._doseCalculator = None

    @property
    def finalDose(self):
        return self._finalDose

    @property
    def finalPlan(self):
        return self._plan

    def abort(self):
        self.cemOptimizer.abort()

    def run(self) -> RTPlan:
        patient = self.ct.patient

        self._computeTargetAndGlobalROIs()

        self._initializePlan()
        #self._initializeAperture()
        beam = self._plan.beams[0]
        if (beam.aperture is None):
            beam.cemToIsocenter = self.apertureToIsocenter

        self._plan.patient = patient
        self.planUpdateEvent.emit(self._plan)

        self._initializeCTWithCEM()
        self._ctWithCEM.name = 'CT with CEM'
        self._ctWithCEM.patient = patient

        self._cropTargetAndGlobalROIsToCT()

        self._initializeCEM()

        self._initializeCEMOptimizer()

        self.cemOptimizer.run(self._plan, self._ctWithCEM)

        # Final dose
        self._computeFinalDose()
        self._finalDose .patient = patient
        self._finalDose .name = 'Final dose'
        self.doseUpdateEvent.emit(self._finalDose )

        return self._plan

    def _computeTargetAndGlobalROIs(self):
        targetROIVal = None
        globalROIVal = None

        for objective in self.objectives:
            obj = objective.objectiveTerm
            roi = obj.roi

            if isinstance(roi, ROIContour):
                roi = roi.getBinaryMask(self.ct.origin, self.ct.gridSize, self.ct.spacing)
            else:
                roi = imageTransform3D.intersect(roi, self.ct, inPlace=False, fillValue=0)

            if (globalROIVal is None):
                globalROIVal = roi.imageArray.astype(bool)
            else:
                globalROIVal = np.logical_or(globalROIVal.astype(bool), roi.imageArray.astype(bool))

            if isinstance(obj, cemObjectives.DoseMinObjective):
                if targetROIVal is None:
                    targetROIVal = roi.imageArray.astype(bool)
                else:
                    targetROIVal = np.logical_or(targetROIVal.astype(bool), roi.imageArray.astype(bool))

        if not self.bodyROI is None:
            if isinstance(self.bodyROI, ROIContour):
                bodyROI = self.bodyROI.getBinaryMask(self.ct.origin, self.ct.gridSize, self.ct.spacing)
            else:
                bodyROI = imageTransform3D.intersect(self.bodyROI, self.ct, inPlace=False, fillValue=0)

            globalROIVal = np.logical_or(globalROIVal.astype(bool), bodyROI.imageArray.astype(bool))

        self._targetROI = ROIMask.fromImage3D(self.ct)
        self._targetROI.imageArray = targetROIVal

        self._globalROI = ROIMask.fromImage3D(self.ct)
        self._globalROI.imageArray = globalROIVal

    def _initializePlan(self):
        self._plan = RTPlan()

        beam = CEMBeam()
        beam.isocenterPosition = self._targetROI.centerOfMass
        beam.gantryAngle = self.gantryAngle
        beam.apertureToIsocenter = self.apertureToIsocenter

        layer = PlanIonLayer(nominalEnergy=self.beamEnergy)
        beam.appendLayer(layer)
        self._plan.appendBeam(beam)

    def _initializeAperture(self):
        #TODO: is there a case where we do not want the aperture?

        beam = self._plan.beams[0]
        aperture = Aperture.fromBeam(self.ct, beam, targetMask=self._targetROI)
        aperture.rsp = self.apertureRSP
        aperture.wet = energyToRange(self.beamEnergy)+10 # 10 is just a margin
        beam.aperture = aperture

        beam.cemToIsocenter = beam.apertureToIsocenter + aperture.wet/aperture.rsp

        self._updateROIsWithAperture()

    def _updateROIsWithAperture(self):
        beam = self._plan.beams[0]
        if beam.aperture is None:
            return

        globalROI = imageTransform3D.intersect(self._globalROI, self.ct, inPlace=False, fillValue=0)
        apertureROI = imageTransform3D.intersect(beam.aperture.computeROI(), self.ct, inPlace=False, fillValue=0)

        globalROI.imageArray = np.logical_or(globalROI.imageArray, apertureROI.imageArray)
        globalROI = imageTransform3D.dicomToIECGantry(globalROI, beam, fillValue=0, cropROI=globalROI, cropDim0=True, cropDim1=True, cropDim2=False)

        self._globalROI = imageTransform3D.iecGantryToDicom(globalROI, beam, fillValue=0)
        imageTransform3D.intersect(self._targetROI, self._globalROI, fillValue=0, inPlace=True)

    def _initializeCTWithCEM(self):
        beam = self._plan.beams[0]

        # Computations are much faster if we crop the CT as much as we can => cropROI=self._globalROI
        ctBEV = imageTransform3D.dicomToIECGantry(self.ct, beam, fillValue=-1024., cropROI=self._globalROI, cropDim0=True, cropDim1=True, cropDim2=False)

        padLength = int(self._padLength() / ctBEV.spacing[2])
        newOrigin = np.array(ctBEV.origin)
        newOrigin[2] = newOrigin[2] - padLength * ctBEV.spacing[2]
        newArray = -1000 * np.ones((ctBEV.gridSize[0], ctBEV.gridSize[1], ctBEV.gridSize[2] + padLength))  # We choose -1000 and not -1024 because we will crop evrthng > -1000
        newArray[:, :, padLength:] = ctBEV.imageArray
        ctBEV.imageArray = newArray
        ctBEV.origin = newOrigin

        ct = imageTransform3D.iecGantryToDicom(ctBEV, beam, fillValue=-1024.)

        if not (beam.aperture is None):
            apertureROI = beam.aperture.computeROI()
            apertureROI = imageTransform3D.intersect(apertureROI, ct, fillValue=0)
            ctArray = ct.imageArray
            ctArray[apertureROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(beam.aperture.rsp, energy=100.)
            ct.imageArray = ctArray

        self._ctWithCEM = ct

    def _cropTargetAndGlobalROIsToCT(self):
        imageTransform3D.intersect(self._targetROI, self._ctWithCEM, fillValue=0, inPlace=True)
        imageTransform3D.intersect(self._globalROI, self._ctWithCEM, fillValue=0, inPlace=True)

    def _initializeCEM(self):
        beam = self._plan.beams[0]
        cem = BiComponentCEM.fromBeam(self._ctWithCEM, beam, targetMask=self._targetROI)
        cem.cemRSP = self.cemRSP
        cem.rangeShifterRSP = self.rangeShifterRSP
        beam.cem = cem

    def _padLength(self) -> float:
        cemThicknessGuess = 50 # Arbitrarily set right now.

        padLength = cemThicknessGuess/self.cemRSP + energyToRange(self.beamEnergy)/self.rangeShifterRSP

        return padLength

    def _initializeCEMOptimizer(self):
        self._initializeObjectives()

        for objective in self.objectives:
            obj = objective.objectiveTerm
            self.cemOptimizer.appendObjective(obj, weight=objective.weight)

        self.cemOptimizer.maxIterations = 25
        self.cemOptimizer.spotSpacing = self.spotSpacing
        self.cemOptimizer.targetMask = self._targetROI
        self.cemOptimizer.absTol = 1.
        self.cemOptimizer.ctCalibration = self.ctCalibration

    def _initializeObjectives(self):
        self._initializeDoseCalculator()

        for objective in self.objectives:
            obj = objective.objectiveTerm
            obj.doseCalculator = self._doseCalculator
            obj.beamModel = self.beamModel
            self.cemOptimizer.appendObjective(obj, weight=objective.weight)

            roi = obj.roi

            if isinstance(roi, ROIContour):
                roi = roi.getBinaryMask(self.ct.origin, self.ct.gridSize, self.ct.spacing)
            else:
                roi = imageTransform3D.intersect(roi, self.ct, inPlace=False, fillValue=0)

            imageTransform3D.intersect(roi, self._ctWithCEM, fillValue=0., inPlace=True)

            obj.roi = roi

    def _initializeDoseCalculator(self):
        self._doseCalculator = CEMDoseCalculator()
        self._doseCalculator.beamModel = self.beamModel
        self._doseCalculator.nbPrimaries = 5e3
        self._doseCalculator.ctCalibration = self.ctCalibration
        self._doseCalculator.plan = self._plan
        self._doseCalculator.roi = self._globalROI
        self._doseCalculator.ct = self._ctWithCEM

    def _computeFinalDose(self):
        # Update CT with CEM
        beam = self._plan.beams[0]
        cem = beam.cem

        [rsROI, cemROI] = beam.cem.computeROIs()

        ctArray = self._ctWithCEM.imageArray
        ctArray[cemROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.cemRSP, energy=100.)
        ctArray[rsROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.rangeShifterRSP, energy=100.)

        self._ctWithCEM.imageArray = ctArray

        # Final dose computation
        doseCalculator = MCsquareDoseCalculator()
        doseCalculator.beamModel = self.beamModel
        doseCalculator.nbPrimaries = 2e7
        doseCalculator.ctCalibration = self.ctCalibration

        self._finalDose  = doseCalculator.computeDose(self._ctWithCEM, self._plan)
