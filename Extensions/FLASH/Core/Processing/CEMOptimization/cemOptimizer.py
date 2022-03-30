import copy
from enum import Enum
from typing import Sequence, Union, Tuple

import numpy as np

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.rspImage import RSPImage
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.sparseBeamlets import SparseBeamlets
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing.imageTransform3D import ImageTransform3D
from Core.event import Event
from Extensions.FLASH.Core.Data.cem import BiComponentCEM
from Extensions.FLASH.Core.Processing.CEMOptimization.cemObjectives import CEMAbstractDoseFidelityTerm
from Extensions.FLASH.Core.Processing.CEMOptimization.cemPlanInitializer import CEMPlanInitializer
from Extensions.FLASH.Core.Processing.CEMOptimization.planOptimizer import PlanOptimizer, PlanOptimizerObjectives
from Extensions.FLASH.Core.Processing.DoseCalculation.analyticalNoScattering import AnalyticalNoScattering
from Extensions.FLASH.Core.Processing.DoseCalculation.fluenceBasedMCsquareDoseCalculator import \
    FluenceBasedMCsquareDoseCalculator, Beamlets
from Extensions.FLASH.Core.Processing.RangeEnergy import rangeToEnergy, energyToRange


class CEMOptimizer:
    class _Objectives(PlanOptimizerObjectives):
        def __init__(self):
            super().__init__()

            self.objectiveWeights = []
            self.objectiveTerms:list[CEMAbstractDoseFidelityTerm] = []

            self._cemArray = None

        @property
        def cemArray(self):
            return np.array(self._cemArray)

        @cemArray.setter
        def cemArray(self, cemVals):
            self._cemArray = np.array(cemVals)

        def append(self, objective:CEMAbstractDoseFidelityTerm, weight:float=1.):
            self.objectiveWeights.append(weight)
            self.objectiveTerms.append(objective)

        def getValue(self, weights:np.ndarray) -> float:
            val = 0
            for i, objectiveTerm in enumerate(self.objectiveTerms):
                val += self.objectiveWeights[i] * objectiveTerm.getValue(weights, self._cemArray)

            return val

        def getDerivative(self, weights:np.ndarray) -> np.ndarray:
            val = 0.
            for i, objectiveTerm in enumerate(self.objectiveTerms):
                val += self.objectiveWeights[i] * objectiveTerm.getWeightDerivative(weights, self._cemArray)

            return val

        def getCEMDerivative(self, weighs:np.ndarray) -> np.ndarray:
            val = 0.
            for i, objectiveTerm in enumerate(self.objectiveTerms):
                val += self.objectiveWeights[i] * objectiveTerm.getCEMDerivative(weighs, self._cemArray)

            return val

    def __init__(self):
        self.maxIterations = 3
        self.spotSpacing = 5
        self.targetMask = None
        self.absTol = 1
        self.ctCalibration:AbstractCTCalibration = None
        self.cemLateralMargin = 5.  # in world unit not pixel

        self.planUpdateEvent = Event(RTPlan)
        self.doseUpdateEvent = Event(object)
        self.fValEvent = Event(Tuple)

        self._ct = None
        self._iteration = 0
        self._plan:RTPlan = None
        self._planInitializer = CEMPlanInitializer()
        self._planOptimizer = PlanOptimizer()
        self._objectives = self._Objectives()
        self._maxStep = 5. # TODO User should be able to set this

    def appendObjective(self, objective: CEMAbstractDoseFidelityTerm, weight: float = 1.):
        self._objectives.append(objective, weight)

    def run(self, plan:RTPlan, ct:CTImage):
        self._plan = plan
        self._ct = ct

        x = self._getCEMFromPlan()
        self._initializePlan()
        spotWeights, cemVal = self._gd(x)

        self._plan.spotWeights = spotWeights
        self._setCEMInPlan(cemVal)

    def _getCEMFromPlan(self) -> np.ndarray:
        cemVal = np.array([])

        for beam in self._plan:
            if beam.cem is None:
                beam.cem = BiComponentCEM.fromBeam(self._ct, beam)

            self._initializeCEM(beam)

            cemArray = beam.cem.imageArray
            if len(cemVal)==0:
                cemVal = cemArray.flatten()
            else:
                cemVal = np.concatenate((cemVal, cemArray.flatten()))

        return cemVal

    def _initializeCEM(self, beam:PlanIonBeam):
        cemArray = beam.cem.imageArray
        cemArray = np.ones(cemArray.shape) * energyToRange(beam.layers[0].nominalEnergy) - self._meanWETOfTarget(beam)

        targetMaskBEV = ImageTransform3D.dicomToIECGantry(self.targetMask, beam, fillValue=0)
        targetMaskBEV.dilate(self.cemLateralMargin)
        targetMask = np.sum(targetMaskBEV.imageArray, 2)
        cemArray[np.logical_not(targetMask.astype(bool))] = 0

        beam.cem.imageArray = cemArray

    def _meanWETOfTarget(self, beam):
        rsp = RSPImage.fromCT(self._ct, self.ctCalibration)
        wepl = rsp.computeCumulativeWEPL(beam)

        weplBEV = ImageTransform3D.dicomToIECGantry(wepl, beam, fillValue=0.)
        roiBEV = ImageTransform3D.dicomToIECGantry(self.targetMask, beam, fillValue=0.)

        weplTarget = weplBEV.imageArray[roiBEV.imageArray.astype(bool)]

        return np.mean(weplTarget)


    def _gd(self, x:np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        self._objectives.cemArray = x
        PlanOptimizer.run(self._objectives, self._plan)

        fVal = self._objectives.getValue(self._plan.spotWeights)
        self.fValEvent.emit((0, fVal))
        self.planUpdateEvent.emit(self._plan)
        doseImage = self._objectives.objectiveTerms[0].doseCalculator.computeDose(self._plan.spotWeights, self._objectives.cemArray)
        self.doseUpdateEvent.emit(doseImage)

        for i in range(self.maxIterations):
            fValPrev = fVal
            xPrev = x
            spotWeightsPrev = np.array(self._plan.spotWeights)

            self._iteration = i

            direction = self._objectives.getCEMDerivative(self._plan.spotWeights)

            x = x + self._maxStep * direction / np.max(np.abs(direction))

            self._objectives.cemArray = x
            PlanOptimizer.run(self._objectives, self._plan)

            fVal = self._objectives.getValue(self._plan.spotWeights)
            self.fValEvent.emit((self._iteration, fVal))
            self.planUpdateEvent.emit(self._plan)
            doseImage = self._objectives.objectiveTerms[0].doseCalculator.computeDose(self._plan.spotWeights, self._objectives.cemArray)
            self.doseUpdateEvent.emit(doseImage)

            if self._iteration>2 and (fValPrev - fVal)<self.absTol:
                return spotWeightsPrev, xPrev

        return self._plan.spotWeights, x

    def _initializePlan(self):
        self._planInitializer.ct = self._ct
        self._planInitializer.plan = self._plan
        self._planInitializer.targetMask = self.targetMask

        self._planInitializer.intializePlan(self.spotSpacing, 0.)

    def _setCEMInPlan(self, cemThickness:np.ndarray):
        ind = 0
        for beam in self._plan:
            cemArray = beam.cem.imageArray
            cemBeamVal = cemThickness[ind:ind + cemArray.shape[0] * cemArray.shape[1]]
            beam.cem.imageArray = np.reshape(cemBeamVal, (cemArray.shape[0], cemArray.shape[1]))

            ind += cemArray.shape[0]*cemArray.shape[1]


class CEMDoseCalculator:
    class DerivativeModes(Enum):
        ANALYTICAL = 'ANALYTICAL'
        DEFAULT = 'ANALYTICAL'
        MC = 'MC'

    def __init__(self):
        self.beamModel = None
        self.ctCalibration:AbstractCTCalibration = None
        self.ct:CTImage = None
        self.plan = None
        self.roi = None
        self.nbPrimaries = 1e4
        self.derivativeMode = self.DerivativeModes.DEFAULT

        self._doseCalculator = MCsquareDoseCalculator()
        self._fluenceDoseCalculator = FluenceBasedMCsquareDoseCalculator()
        self._analyticalCalculator = AnalyticalNoScattering()

        self._ctCEFForBeamlets = None
        self._weightsForBeamlets = np.array([])
        self._cemThicknessForBeamlets = np.array([])

        self._cemThicknessForDerivative = np.array([])
        self._weightsForDerivative = np.array([])

        self._sparseDerivativeCEM = None
        self._analyticalDerivative = None
        self._dose:DoseImage = None
        self._beamlets:SparseBeamlets = None

        self.iteration = 0 # debug

    def computeDose(self, weights:np.ndarray, cemThickness:np.ndarray) -> DoseImage:
        if self._doseMustBeRecomputed(weights, cemThickness):
            self.computeBeamlets(cemThickness)
            self._updateDose(weights)

        return self._dose

    def _doseMustBeRecomputed(self, weights:np.ndarray, cemThickness:np.ndarray):
        if len(self._weightsForBeamlets)==0:
            return True

        return not(np.allclose(weights, self._weightsForBeamlets, atol=0.1)) or self._beamletsMustBeRecomputed(cemThickness)

    def _beamletsMustBeRecomputed(self, cemThickness:np.ndarray) -> bool:
        if len(self._cemThicknessForBeamlets)==0:
            return True

        return not np.allclose(cemThickness, self._cemThicknessForBeamlets, atol=0.1)

    def _updateDose(self, weights:np.ndarray):
        self._weightsForBeamlets = np.array(weights)
        self._beamlets.beamletWeights = self._weightsForBeamlets
        self._dose = self._beamlets.toDoseImage()

    def computeBeamlets(self, cemThickness: np.ndarray) -> SparseBeamlets:
        if self._beamletsMustBeRecomputed(cemThickness):
            self._updateCTForBeamletsWithCEM(cemThickness)
            self._updateBeamlets()

        return self._beamlets

    def _updateCTForBeamletsWithCEM(self, cemThickness:np.ndarray):
        self._ctCEFForBeamlets = CTImage.fromImage3D(self.ct)

        ind = 0
        for beam in self.plan:
            beam.cem.patient = None # We do not want to deepcopy patient field!
            cem = copy.deepcopy(beam.cem)

            cemArray = beam.cem.imageArray
            cemBeamVal = cemThickness[ind:ind+cemArray.shape[0]*cemArray.shape[1]]
            beam.cem.imageArray = np.reshape(cemBeamVal, (cemArray.shape[0], cemArray.shape[1]))

            [rsROI, cemROI] = beam.cem.computeROIs(self.ct, beam)

            ctArray = self._ctCEFForBeamlets.imageArray
            ctArray[cemROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.cemRSP, energy=100.)
            ctArray[rsROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.rangeShifterRSP, energy=100.)
            self._ctCEFForBeamlets.imageArray = ctArray

            ind += cemArray.shape[0]*cemArray.shape[1]

        self._cemThicknessForBeamlets = np.array(cemThickness)

    def _updateBeamlets(self):
        self._doseCalculator.beamModel = self.beamModel
        self._doseCalculator.ctCalibration = self.ctCalibration
        self._doseCalculator.nbPrimaries = self.nbPrimaries

        self._beamlets = self._doseCalculator.computeBeamlets(self._ctCEFForBeamlets, self.plan, self.roi)

    def computeDerivative(self, weights:np.ndarray, cemThickness:np.ndarray) -> Union[Beamlets, Sequence[DoseImage]]:
        if self.derivativeMode==self.DerivativeModes.ANALYTICAL:
            return self.computeAnalyticalDerivative(weights, cemThickness)
        elif self.derivativeMode==self.DerivativeModes.MC:
            return self.computeBeamletDerivative(weights, cemThickness)
        else:
            raise ValueError('derivativeMode is incorrect')

    def computeAnalyticalDerivative(self, weights:np.ndarray, cemThickness:np.ndarray) -> Sequence[DoseImage]:
        if self._derivativeMustBeRecomputed(weights, cemThickness):
            self._cemThicknessForDerivative = np.array(cemThickness)
            self._weightsForDerivative = np.array(weights)
            self._updateAnalyticalDerivative()

        return self._analyticalDerivative

    def _derivativeMustBeRecomputed(self, weights:np.ndarray, cemThickness:np.ndarray) -> bool:
        if len(self._cemThicknessForDerivative)==0:
            return True

        if len(self._weightsForDerivative)==0:
            return True

        return not(np.allclose(cemThickness, self._cemThicknessForDerivative, atol=0.1) and np.allclose(weights, self._weightsForDerivative, atol=0.1))

    def _updateAnalyticalDerivative(self):
        deltaR = 0.1

        self._analyticalCalculator.beamModel = self.beamModel
        self._analyticalCalculator.ctCalibration = self.ctCalibration

        plan = copy.deepcopy(self.plan)
        plan.spotWeights = self._weightsForDerivative

        ind = 0
        for beam in plan:
            cemArray = beam.cem.imageArray
            cemBeamVal = self._cemThicknessForDerivative[ind:ind+cemArray.shape[0]*cemArray.shape[1]]
            beam.cem.imageArray = np.reshape(cemBeamVal, (cemArray.shape[0], cemArray.shape[1]))

            ind += cemArray.shape[0]*cemArray.shape[1]

        doseSequence = self._analyticalCalculator.computeDosePerBeam(self.ct, plan)

        plan2 = self._lowerPlanEnergy(plan, deltaR=deltaR)
        doseSequence2 = self._analyticalCalculator.computeDosePerBeam(self.ct, plan2)

        derivSequence = []
        for i, dose in enumerate(doseSequence):
            dose.imageArray = (dose.imageArray - doseSequence2[i].imageArray)/deltaR
            outDose = DoseImage.fromImage3D(dose)
            outDose = ImageTransform3D.dicomToIECGantry(outDose, plan.beams[i], fillValue=0.)
            derivSequence.append(outDose)

        self._analyticalDerivative = derivSequence

    def computeBeamletDerivative(self, weights:np.ndarray, cemThickness: np.ndarray) -> Beamlets:
        if not (np.array_equal(cemThickness, self._cemThicknessForDerivative) and np.array_equal(weights, self._weightsForDerivative)):
            self._cemThicknessForDerivative = cemThickness
            self._weightsForDerivative = weights
            self._updateBeamletDerivative()

        return self._sparseDerivativeCEM


    def _updateBeamletDerivative(self):
        self._fluenceDoseCalculator.beamModel = self.beamModel
        self._fluenceDoseCalculator.ctCalibration = self.ctCalibration
        self._fluenceDoseCalculator.nbPrimaries = 1e4

        beamlets = self._fluenceDoseCalculator.computeBeamlets(self._ctCEFForBeamlets, self.plan, self.roi)

        plan2 = self._lowerPlanEnergy(self.plan, deltaR=1.)
        beamletsE2 = self._fluenceDoseCalculator.computeBeamlets(self._ctCEFForBeamlets, plan2, self.roi)

        sparseBeamlets = beamlets.sparseBeamlets
        sparseBeamlets.setUnitaryBeamlets(sparseBeamlets.toSparseMatrix() - beamletsE2.sparseBeamlets.toSparseMatrix())
        beamlets.sparseBeamlets = sparseBeamlets

        self._sparseDerivativeCEM = beamlets

    def _lowerPlanEnergy(self, plan:RTPlan, deltaR:float=1.) -> RTPlan:
        plan2 = copy.deepcopy(plan)

        for beam in plan2:
            for layer in beam:
                layer.nominalEnergy = rangeToEnergy(energyToRange(layer.nominalEnergy)-deltaR)

        return plan2
