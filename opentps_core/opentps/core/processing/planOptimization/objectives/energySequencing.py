from numpy import matlib as mb
import numpy as np
from scipy.special import logsumexp

from opentps.core.processing.planOptimization import tools
from opentps.core.processing.planOptimization.objectives.baseFunction import BaseFunc


class EnergySeq(BaseFunc):
    """
    Energy sequencing function (eval, grad): regularization used to sequence
    the energy layers by descending order (favor high-to-low energy sequence)
    gamma is the regularization parameter. Inherited from BaseFunc.

    Attributes
    ----------
    plan : Plan
        Plan of which the energy sequencing function is calculated.
    gamma : float
        Regularization parameter.
    factor : float
        Factor used to scale the energy sequencing function.
    """

    def __init__(self, plan, gamma, factor=0.001, **kwargs):
        self.gamma = gamma
        self.struct = tools.WeightStructure(plan)
        self.factor = factor
        super(EnergySeq, self).__init__(**kwargs)

    def _eval(self, x):
        beamLayerStruct = self.struct.getBeamStructure(x)

        beamElements = np.zeros(self.struct.nBeams)
        for i, beam in enumerate(beamLayerStruct):
            # vector of size nOfLayers in beam i
            # contains sum of weights in each layer of beam i

            yb = np.zeros(len(beam))
            for j, layer in enumerate(beam):
                yb[j] = np.sum(layer)

            yb[:] = self.factor * yb
            sigmoidYb = np.tanh(yb)
            energies = np.multiply(self.struct.energyLayers[i], sigmoidYb)
            LSE = logsumexp(energies)
            beamElements[i] = LSE

        deltaE = np.diff(beamElements)
        leakyReluDeltaE = [0.01 * elem if elem < 0 else elem for elem in deltaE]
        res = np.sum(leakyReluDeltaE)

        return res * self.gamma

    def _grad(self, x):
        beamLayerStruct = self.struct.getBeamStructure(x)
        res = []
        gradX = [[]]
        beamKs = []
        beamYbs = []
        for i, beam in enumerate(beamLayerStruct):
            yb = np.zeros(len(beam))
            for j, layer in enumerate(beam):
                yb[j] = np.sum(layer)
            zb = self.struct.energyLayers[i]
            Kb = np.multiply(zb, np.tanh(self.factor * yb))

            beamYbs.append(yb)
            beamKs.append(Kb)

        # first beam
        y1 = beamYbs[0]
        z1 = np.array(self.struct.energyLayers[0])
        K1 = beamKs[0]
        tmp = (np.exp(K1) / np.sum(np.exp(K1))) * (z1 * self.factor * (1 - (np.tanh(self.factor * y1) ** 2)))
        expr = logsumexp(beamKs[1]) - logsumexp(K1)
        if expr < 0:
            cFirst = 0.01
        else:
            cFirst = 1.
        # should be a vector of size nOfLayers in first beam
        res.append(- cFirst * tmp)

        # intermediate
        for i, beam in enumerate(beamLayerStruct, start=1):
            if i >= len(beamLayerStruct) - 1:
                break
            yb = beamYbs[i]
            zb = np.array(self.struct.energyLayers[i])
            Kb = beamKs[i]
            tmp = (np.exp(Kb) / np.sum(np.exp(Kb))) * (zb * self.factor * (1 - (np.tanh(self.factor * yb) ** 2)))

            expr1 = logsumexp(Kb) - logsumexp(beamKs[i - 1])
            expr2 = logsumexp(beamKs[i + 1]) - logsumexp(Kb)
            if expr1 < 0:
                c1 = 0.01
            else:
                c1 = 1.0
            if expr2 < 0:
                c2 = 0.01
            else:
                c2 = 1.0

            # should be a vector of size nOfLayers in beam i
            res.append(c1 * tmp - c2 * tmp)

        # last beam
        yB = beamYbs[-1]
        zB = np.array(self.struct.energyLayers[-1])

        KB = beamKs[-1]
        tmpLast = (np.exp(KB) / np.sum(np.exp(KB))) * (zB * self.factor * (1 - (np.tanh(self.factor * yB) ** 2)))

        exprLast = np.log(np.sum(np.exp(KB))) - np.log(np.sum(np.exp(beamKs[-2])))
        if exprLast < 0.:
            cLast = 0.01
        else:
            cLast = 1.0
        # should be a vector of size nOfLayers in last beam
        res.append(cLast * tmpLast)

        flatRes = [item for sublist in res for item in sublist]

        for layer in range(len(flatRes)):
            tmp = mb.repmat(flatRes[layer], 1, self.struct.nSpotsInLayer[layer])
            gradX = np.concatenate((gradX, tmp), axis=1)

        gradX = gradX.flatten()

        return gradX * self.gamma
