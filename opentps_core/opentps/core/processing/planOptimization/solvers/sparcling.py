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
            initialResult = solver.solve(func, x0)


    def splitBeams(self):
        newBeams = []
        for beam in self.plan.Beams:
            # create sub-beams
            beam1 = beam.__deepcopy__
            beam1.gantryAngle = beam.gantryAngle - self.angularStep / 2
            if beam1.gantryAngle < 0: beam1.gantryAngle += 360
            if beam1.gantryAngle >= 360: beam1.gantryAngle -= 360
            beam2 = beam.__deepcopy__
            beam2.GantryAngle = beam.gantryAngle + self.angularStep / 2
            if beam2.gantryAngle < 0: beam2.gantryAngle += 360
            if beam2.gantryAngle >= 360: beam2.gantryAngle -= 360

            if len(beam.layers) == 1:
                layer = beam.layers[0].__deepcopy__
                beam1.Layers[-1] = layer
                layer2 = beam.layers[0].__deepcopy__
                beam2.Layers[-1] = layer2

            else:
                MU1 = MU2 = 0
                for j, layer in enumerate(beam.layers):
                    if j < int(len(beam.layers) / 2):
                        MU1 += sum(layer.ScanSpotMetersetWeights)
                    else:
                        MU2 += sum(layer.ScanSpotMetersetWeights)

                beam1.Layers = beam.layers[:int(len(beam.layers) / 2)]
                beam2.Layers = beam.layers[int(len(beam.layers) / 2): len(beam.layers)]

            newBeams.append(beam1)
            newBeams.append(beam2)

        self.plan.Beams = newBeams

    def removeLayers(self):
        # this function already exists in rtplan - might use it instead
        pass

    def removeBeams(self):
        # this function already exists in rtplan - might use it instead
        pass
