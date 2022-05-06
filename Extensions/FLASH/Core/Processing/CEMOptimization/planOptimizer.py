
import numpy as np
from scipy.optimize import minimize, Bounds

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.sparseBeamlets import SparseBeamlets
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Extensions.FLASH.Core.Processing.CEMOptimization.planObjectives import AbstractDoseFidelityTerm


class PlanOptimizerObjectives:
    def __init__(self):
        self.objectiveWeights = []
        self.objectiveTerms = []

    def append(self, objective: AbstractDoseFidelityTerm, weight: float = 1.):
        self.objectiveWeights.append(weight)
        self.objectiveTerms.append(objective)

    def getValue(self, weights: np.ndarray) -> float:
        val = 0
        for i, objectiveTerm in enumerate(self.objectiveTerms):
            val += self.objectiveWeights[i] * objectiveTerm.getValue(weights)

        return val

    def getDerivative(self, weights: np.ndarray) -> np.ndarray:
        val = 0.
        for i, objectiveTerm in enumerate(self.objectiveTerms):
            val += self.objectiveWeights[i] * objectiveTerm.getDerivative(weights)

        return val

class PlanOptimizer:
    @staticmethod
    def run(objectives:PlanOptimizerObjectives, plan:RTPlan):
        res = minimize(objectives.getValue, np.ones(plan.spotWeights.shape),
                        method='L-BFGS-B',
                        jac=objectives.getDerivative,
                        tol=None, callback=None,
                        options={'disp': True, 'maxcor': 10, 'ftol': 1e-4, 'gtol': 1e-4, 'norm': 1,
                           'maxfun': 15000, 'maxiter': 200, 'iprint': -1, 'maxls': 10, 'finite_diff_rel_step': None},
                        bounds=Bounds(0., 9999.))

        plan.spotWeights = res.x

class PlanDoseCalculator:
    def __init__(self):
        self.beamModel = None
        self.ctCalibration = None
        self.ct = None
        self.plan = None
        self.roi = None
        self.nbPrimaries = 1e4
        self._doseCalculator = MCsquareDoseCalculator()

        self._weights:np.ndarray = None
        self._dose:DoseImage = None
        self._beamlets:SparseBeamlets = None

    def kill(self):
        self._doseCalculator.kill()

    def computeDose(self, weights:np.ndarray) -> DoseImage:
        if not np.array_equal(weights, self._weights):
            self._weights = weights
            self._recomputeDose()

        return self._dose

    def computeBeamlets(self) -> SparseBeamlets:
        if self._beamlets is None:
            self._recomputeBeamlets()

        return self._beamlets

    def _recomputeBeamlets(self):
        self._doseCalculator.beamModel = self.beamModel
        self._doseCalculator.ctCalibration = self.ctCalibration
        self._doseCalculator.nbPrimaries = self.nbPrimaries

        self._beamlets = self._doseCalculator.computeBeamlets(self.ct, self.plan, self.roi)

    def _recomputeDose(self):
        if self._beamlets is None:
            self._recomputeBeamlets()

        self._beamlets.beamletWeights = self._weights
        self._dose = self._beamlets.toDoseImage()
