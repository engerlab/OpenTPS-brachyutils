
import numpy as np
from scipy.optimize import minimize

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.beamletDose import BeamletDose
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Extensions.FLASH.Core.Processing.CEMOptimization.planInitializer import PlanInitializer
from Extensions.FLASH.Core.Processing.CEMOptimization.planObjectives import AbstractDoseFidelityTerm


class PlanOptimizer:
    class _Objectives:
        def __init__(self):
            self.objectiveWeights = []
            self.objectiveTerms = []

        def append(self, objective:AbstractDoseFidelityTerm, weight:float=1.):
            self.objectiveWeights.append(weight)
            self.objectiveTerms.append(objective)

        def getValue(self, weights:np.ndarray) -> float:
            val = 0
            for i, objectiveTerm in enumerate(self.objectiveTerms):
                val += self.objectiveWeights[i]*objectiveTerm.getValue(weights)

            print('Mean w: ' + str(np.mean(weights)))
            print('Objective value: ' + str(val))

            return val

        def getDerivative(self, weights:np.ndarray) -> np.ndarray:
            val = 0.
            for i, objectiveTerm in enumerate(self.objectiveTerms):
                val += self.objectiveWeights[i]*objectiveTerm.getDerivative(weights)

            return val

    def __init__(self):
        self.ctCalibration:AbstractCTCalibration=None
        self.ct:CTImage=None
        self.plan:RTPlan=None
        self.targetMask:ROIMask=None

        self._objectives = self._Objectives()

    def appendObjective(self, objective:AbstractDoseFidelityTerm, weight:float=1.):
        self._objectives.append(objective, weight)

    def intializePlan(self, spotSpacing:float, layerSpacing:float, targetMargin:float=0.):
        planInitializer = PlanInitializer()
        planInitializer.calibration = self.ctCalibration
        planInitializer.ct = self.ct
        planInitializer.plan = self.plan
        planInitializer.targetMask = self.targetMask

        planInitializer.intializePlan(spotSpacing, layerSpacing, targetMargin)

    def run(self):
        res = minimize(self._objectives.getValue, np.ones(self.plan.spotWeights.shape),
                        method='L-BFGS-B',
                        jac=self._objectives.getDerivative,
                        bounds=None, tol=None, callback=None,
                        options={'disp': True, 'maxcor': 10, 'ftol': 1e-4, 'gtol': 1e-4, 'norm': 1,
                           'maxfun': 15000, 'maxiter': 200, 'iprint': -1, 'maxls': 5, 'finite_diff_rel_step': None})

        self.plan.spotWeights = res.x

class CacheDoseCalculator:
    def __init__(self):
        self.beamModel = None
        self.ctCalibration = None
        self.ct = None
        self.plan = None
        self.nbPrimaries = 1e4
        self._doseCalculator = MCsquareDoseCalculator()

        self._weights:np.ndarray = None
        self._dose:DoseImage = None
        self._beamlets:BeamletDose = None

    def computeDose(self, weights:np.ndarray) -> DoseImage:
        if not np.array_equal(weights, self._weights):
            self._weights = weights
            self._recomputeDose()

        return self._dose

    def computeBeamlets(self) -> BeamletDose:
        if self._beamlets is None:
            self._recomputeBeamlets()

        return self._beamlets

    def _recomputeBeamlets(self):
        self._doseCalculator.beamModel = self.beamModel
        self._doseCalculator.ctCalibration = self.ctCalibration
        self._doseCalculator.nbPrimaries = self.nbPrimaries

        self._beamlets = self._doseCalculator.computeBeamlets(self.ct, self.plan)

    def _recomputeDose(self):
        if self._beamlets is None:
            self._recomputeBeamlets()

        self._beamlets.beamletWeights = self._weights
        self._dose = self._beamlets.toDoseImage()
