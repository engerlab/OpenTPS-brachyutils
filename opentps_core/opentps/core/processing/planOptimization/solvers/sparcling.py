from opentps.core.processing.planOptimization.solvers.beamletFree import BLFree


class SPArCling:
    def __init__(self, arcStart, arcStop, maxNSplitting, finalAngleStep, mode='BLFree', **kwargs):
        super(SPArCling, self).__init__(**kwargs)
        self.mode = mode
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

    def solve(self):
        # step 1: optimize initial plan
        if self.mode == "beamletFree":
            pass
        else:
            solver = IMPTPlanOptimizer(self.meth)
            #w, doseVector, ps =

        while self.angularStep > 1.5:
            self.angularStep /= 2
            self.splitBeams()
            if self.mode == "beamletFree":
                mhdDose = BLFree(self.ct, self.plan, self.contours)

            else:
                pass


    def splitBeams(self):
        pass

    def removeLayers(self):
        # this function already exists in rtplan - might use it instead
        pass

    def removeBeams(self):
        # this function already exists in rtplan - might use it instead
        pass
