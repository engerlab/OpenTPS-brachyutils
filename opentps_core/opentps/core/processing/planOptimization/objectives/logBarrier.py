import numpy as np
from numpy import matlib as mb
from opentps.core.processing.planOptimization.tools import WeightStructure
from opentps.core.processing.planOptimization.objectives.baseFunction import BaseFunc


class LogBarrier(BaseFunc):
    """
    Log barrier function (eval, grad): regularization function used to distribute
    the selected layers to the whole gantry rotating range. The term sums up
    the intensity of each beam and penalizes the zero intensities,
    therefore forcing each beam to keep at least one layer selected.
    beta is the regularization parameter for the log barrier function
    """

    def __init__(self, plan, beta, **kwargs):
        self.beta = beta
        self.struct = WeightStructure(plan)
        super(LogBarrier, self).__init__(**kwargs)

    def logCols(self, x):
        """ Calculates log of each beam"""
        res = np.zeros(len(x))
        for beam in range(len(x)):
            for layer in range(len(x[beam])):
                res[beam] += np.sum(x[beam][layer])
        return np.log(np.where(res > 0., res, 1e-300))

    def _eval(self, x):
        beamLayerStruct = self.struct.getBeamStructure(x)
        res = - self.beta * np.sum(self.logCols(beamLayerStruct))
        return res

    def _grad(self, x):
        beamLayerStruct = self.struct.getBeamStructure(x)
        res = -self.beta * self.dlogCols(beamLayerStruct)
        return res

    def dlogCols(self, x):
        """ Calculates derivative log of each layer and sum in each beam"""
        X = [[]]
        layerSum = np.zeros(len(x))
        for beam in range(len(x)):
            for layer in range(len(x[beam])):
                layerSum[beam] += np.sum(x[beam][layer])
        layerSum[:] = np.reciprocal(np.where(layerSum > 0., layerSum, 1e-300))
        for beam in range(len(layerSum)):
            tmp = mb.repmat(layerSum[beam], 1, self.struct.nSpotsInBeam[beam])
            X = np.concatenate((X, tmp), axis=1)

        res = X.flatten()

        return res
