
from typing import Tuple

import numpy as np

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.rspImage import RSPImage
from Core.Data.Plan.rtPlan import RTPlan
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Core.event import Event
from Extensions.FLASH.Core.Data.cem import BiComponentCEM
from Extensions.FLASH.Core.Processing.CEMOptimization.cemDoseCalculator import CEMDoseCalculator
from Extensions.FLASH.Core.Processing.CEMOptimization.cemObjectives import CEMAbstractDoseFidelityTerm
from Extensions.FLASH.Core.Processing.CEMOptimization.cemPlanInitializer import CEMPlanInitializer
from Extensions.FLASH.Core.Processing.CEMOptimization.planOptimizer import PlanOptimizer, PlanOptimizerObjectives
from Extensions.FLASH.Core.Processing.RangeEnergy import energyToRange

class AbortedException(Exception):
    pass

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

        def kill(self):
            for objective in self.objectiveTerms:
                objective.doseCalculator.kill()

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

        self.planUpdateEvent = Event(RTPlan)
        self.doseUpdateEvent = Event(object)
        self.fValEvent = Event(Tuple)

        self._abort = False
        self._ct = None
        self._iteration = 0
        self._plan:RTPlan = None
        self._planInitializer = CEMPlanInitializer()
        self._planOptimizer = PlanOptimizer()
        self._objectives = self._Objectives()
        self._maxStep = 8. # TODO User should be able to set this

    def appendObjective(self, objective: CEMAbstractDoseFidelityTerm, weight: float = 1.):
        self._objectives.append(objective, weight)

    def abort(self):
        self._abort = True
        self._objectives.kill()

    def run(self, plan:RTPlan, ct:CTImage):
        self._abort = False

        self._plan = plan
        self._ct = ct

        self._initializeCEM()
        self._initializePlan()

        cemVal = self._getCEMValFromPlan()

        try:
            spotWeights, cemVal = self._gd(cemVal)
        except Exception as e:
            raise e from e
        finally:
            self._abort = False

        self._plan.spotWeights = spotWeights
        self._setCEMValInPlan(cemVal)

    def _initializeCEM(self):
        for beam in self._plan:
            if beam.cem is None:
                beam.cem = BiComponentCEM.fromBeam(self._ct, beam, targetMask=self.targetMask)

            cemArray = beam.cem.imageArray
            cemArray = np.ones(cemArray.shape) * energyToRange(beam.layers[0].nominalEnergy) - self._meanWETOfTarget(beam)

            cropROIBEV = imageTransform3D.dicomToIECGantry(beam.cem.targetMask, beam, fillValue=0,
                                                           cropROI=beam.cem.targetMask, cropDim0=True, cropDim1=True, cropDim2=False)

            cropMask = np.sum(cropROIBEV.imageArray, 2)

            #TODO: check that cropMask has same spatial referencing as CEM
            cemArray[np.logical_not(cropMask.astype(bool))] = 0

            beam.cem.imageArray = cemArray

    def _getCEMValFromPlan(self) -> np.ndarray:
        cemVal = np.array([])

        for beam in self._plan:
            cemArray = beam.cem.imageArray
            if len(cemVal)==0:
                cemVal = cemArray.flatten()
            else:
                cemVal = np.concatenate((cemVal, cemArray.flatten()))

        return cemVal

    def _setCEMValInPlan(self, cemThickness:np.ndarray):
        ind = 0
        for beam in self._plan:
            cemArray = beam.cem.imageArray
            cemBeamVal = cemThickness[ind:ind + cemArray.shape[0] * cemArray.shape[1]]
            beam.cem.imageArray = np.reshape(cemBeamVal, (cemArray.shape[0], cemArray.shape[1]))

            ind += cemArray.shape[0]*cemArray.shape[1]

    def _meanWETOfTarget(self, beam):
        rsp = RSPImage.fromCT(self._ct, self.ctCalibration)
        wepl = rsp.computeCumulativeWEPL(beam, roi=self.targetMask)

        weplBEV = imageTransform3D.dicomToIECGantry(wepl, beam, fillValue=0., cropROI=self.targetMask, cropDim0=True, cropDim1=True, cropDim2=False)
        roiBEV = imageTransform3D.dicomToIECGantry(self.targetMask, beam, fillValue=0., cropROI=self.targetMask, cropDim0=True, cropDim1=True, cropDim2=False)

        weplTarget = weplBEV.imageArray[roiBEV.imageArray.astype(bool)]

        return np.mean(weplTarget)

    def _initializePlan(self):
        self._planInitializer.ct = self._ct
        self._planInitializer.plan = self._plan
        self._planInitializer.targetMask = self.targetMask

        self._planInitializer.intializePlan(self.spotSpacing, targetMargin=0.)

    def _gd(self, x:np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        doseCalculator:CEMDoseCalculator = self._objectives.objectiveTerms[0].doseCalculator

        self._objectives.cemArray = x
        PlanOptimizer.run(self._objectives, self._plan)

        fVal = self._objectives.getValue(self._plan.spotWeights)
        self.fValEvent.emit((0, fVal))
        self.planUpdateEvent.emit(self._plan)
        doseImage = doseCalculator.computeDose(self._plan.spotWeights, self._objectives.cemArray)
        self.doseUpdateEvent.emit(doseImage)

        for i in range(self.maxIterations):
            if self._abort:
                raise AbortedException()

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
            doseImage = doseCalculator.computeDose(self._plan.spotWeights, self._objectives.cemArray)
            self.doseUpdateEvent.emit(doseImage)

            if self._iteration>2 and (fValPrev - fVal)<self.absTol:
                # TODO We assume that this will change doseCalculator of all objectives but is it true/OK?
                if doseCalculator.derivativeMode==doseCalculator.DerivativeModes.ANALYTICAL:
                    doseCalculator.derivativeMode = doseCalculator.DerivativeModes.MC
                    self._plan.spotWeights = spotWeightsPrev
                    self._objectives.cemArray = xPrev

                    fVal = fValPrev
                    x = xPrev

                    self._maxStep = self._maxStep/2.
                else:
                    return spotWeightsPrev, xPrev

        return self._plan.spotWeights, x
