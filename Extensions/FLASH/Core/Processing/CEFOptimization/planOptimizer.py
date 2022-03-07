
import numpy as np
from scipy.optimize import minimize

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.rtPlan import RTPlan
from Extensions.FLASH.Core.Processing.CEFOptimization.planInitializer import PlanInitializer
from Extensions.FLASH.Core.Processing.CEFOptimization.planObjectives import AbstractDoseFidelityTerm


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

            return val

        def getDerivative(self, weights:np.ndarray) -> np.ndarray:
            val = 0
            for i, objectiveTerm in enumerate(self.objectiveTerms):
                val += self.objectiveWeights[i]*objectiveTerm.getDerivative(weights)

            return val

    def __init__(self):
        self.calibration:AbstractCTCalibration=None
        self.ct:CTImage=None
        self.plan:RTPlan=None
        self.targetMask:ROIMask=None

        self._objectives = self._Objectives()

    def appendObjective(self, objective:AbstractDoseFidelityTerm, weight:float=1.):
        self._objectives.append(objective, weight)

    def intializePlan(self, spotSpacing:float, layerSpacing:float, targetMargin:float=0.):
        planInitializer = PlanInitializer()
        planInitializer.calibration = self.calibration
        planInitializer.ct = self.ct
        planInitializer.plan = self.plan
        planInitializer.targetMask = self.targetMask

        planInitializer.intializePlan(spotSpacing, layerSpacing, targetMargin)

    def run(self):
        res = minimize(self._objectives.getValue, np.array(self.plan.spotWeights),
                       method='L-BFGS-B',
                       jac=self._objectives.getDerivative,
                       bounds=None, tol=None, callback=None,
                       options={'disp': None, 'maxcor': 10, 'ftol': 1e-6, 'gtol': 1e-6, 'eps': 1e-08,
                          'maxfun': 15000, 'maxiter': 200, 'iprint': 101, 'maxls': 20, 'finite_diff_rel_step': None})

        self.plan.spotWeights = res.x