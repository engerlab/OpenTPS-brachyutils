from opentps.core.processing.planOptimization.solvers import bfgs, gradientDescent, lp
from opentps.core.data.plan._planIonLayer import PlanIonLayer
from opentps.core.data.plan._planIonBeam import PlanIonBeam


class SPArCling:
    def __init__(self, plan, arcStart, arcStop, maxNSplitting, finalAngleStep, mode='BLBased',
                 coreOptimizer='Scipy-LBFGS',
                 **kwargs):
        super(SPArCling, self).__init__(**kwargs)
        self.plan = plan
        self.mode = mode
        self.coreOptimizer = coreOptimizer
        self.arcStart = arcStart
        self.arcStop = arcStop
        self.maxNSplitting = maxNSplitting
        self.finalAngleStep = finalAngleStep
        self.M = 2

        self.angularStep = -self.finalAngleStep * 2 ** self.maxNSplitting
        self.theta1 = (1 - 2 ** (-self.maxNSplitting)) * self.angularStep / 2 + self.arcStart
        self.theta2 = self.arcStop - (
                (1 - 2 ** (-self.maxNSplitting)) * self.angularStep / 2 + self.M * self.angularStep)
        self.minTheta = min(self.theta1, self.theta2)
        self.theta0 = (1 / 2) * abs(self.theta1 - self.theta2) + self.minTheta

    def solve(self, func, x0, **kwargs):
        # Pick beamlet-free or beamlet-based mode
        if self.mode == "BLFree":
            raise NotImplementedError
        else:
            raise NotImplementedError

            if self.coreOptimizer == "Scipy-LBFGS":
                solver = bfgs.ScipyOpt('BFGS', **kwargs)
            elif self.coreOptimizer == 'Scipy-LBFGS':
                solver = bfgs.ScipyOpt('L-BFGS-B', **kwargs)
            elif self.coreOptimizer == 'Gradient':
                solver = gradientDescent.GradientDescent(**kwargs)
            elif self.coreOptimizer == 'BFGS':
                solver = bfgs.BFGS(**kwargs)
            elif self.coreOptimizer == "lBFGS":
                solver = bfgs.LBFGS(**kwargs)
            elif self.coreOptimizer == "LP":
                solver = lp.LP(self.plan, **kwargs)

            # step 1: optimize initial plan
            #initialResult = solver.solve(func, x0)


    def splitBeams(self):
        pass

    def removeLayers(self):
        # this function already exists in rtplan - might use it instead
        pass

    def removeBeams(self):
        # this function already exists in rtplan - might use it instead
        pass
