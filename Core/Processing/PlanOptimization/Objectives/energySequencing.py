from numpy import matlib as mb
import numpy as np
from scipy.special import logsumexp

from Core.Processing.PlanOptimization import tools
from Core.Processing.PlanOptimization.Objectives.baseFunction import BaseFunc


class EnergySeq(BaseFunc):
    """
    Energy sequencing function (eval, grad): regularization used to sequence
    the energy layers by descending order (favor high-to-low energy sequence)
    gamma is the regularization parameter.
    """

    def __init__(self, plan, gamma, factor, **kwargs):
        self.gamma = gamma
        self.struct = tools.weightStructure(plan)
        self.factor = factor
        super(EnergySeq, self).__init__(**kwargs)

    def _eval(self, x):
        beamLayerStruct = self.struct.beamStructure(x)

        beamElements = np.zeros(self.struct.nBeams)
        for i, beam in enumerate(beamLayerStruct):
            # vector of size nOfLayers in beam i
            # contains sum of weights in each layer of beam i

            y_b = np.zeros(len(beam))
            for j, layer in enumerate(beam):
                y_b[j] = np.sum(layer)

            y_b[:] = self.factor * y_b
            sigmoid_yb = np.tanh(y_b)
            energies = np.multiply(self.struct.energyLayers[i], sigmoid_yb)
            LSE = logsumexp(energies)
            beamElements[i] = LSE

        deltaE = np.diff(beamElements)
        leakyRelu_deltaE = [0.01 * elem if elem < 0 else elem for elem in deltaE]
        res = np.sum(leakyRelu_deltaE)

        return res * self.gamma

    def _grad(self, x):
        beamLayerStruct = self.struct.beamStructure(x)
        res = []
        X = [[]]
        beam_Ks = []
        beam_ybs = []
        for i, beam in enumerate(beamLayerStruct):
            y_b = np.zeros(len(beam))
            for j, layer in enumerate(beam):
                y_b[j] = np.sum(layer)
            z_b = self.struct.energyLayers[i]
            K_b = np.multiply(z_b, np.tanh(self.factor * y_b))

            beam_ybs.append(y_b)
            beam_Ks.append(K_b)

        # first beam
        y_1 = beam_ybs[0]
        z_1 = np.array(self.struct.energyLayers[0])
        K_1 = beam_Ks[0]
        tmp = (np.exp(K_1) / np.sum(np.exp(K_1))) * (z_1 * self.factor * (1 - (np.tanh(self.factor * y_1) ** 2)))
        expr = logsumexp(beam_Ks[1]) - logsumexp(K_1)
        if expr < 0:
            c_first = 0.01
        else:
            c_first = 1.
        # should be a vector of size nOfLayers in first beam
        res.append(- c_first * tmp)

        # intermediate
        for i, beam in enumerate(beamLayerStruct, start=1):
            if i >= len(beamLayerStruct) - 1:
                break
            y_b = beam_ybs[i]
            z_b = np.array(self.struct.energyLayers[i])
            K_b = beam_Ks[i]
            tmp = (np.exp(K_b) / np.sum(np.exp(K_b))) * (z_b * self.factor * (1 - (np.tanh(self.factor * y_b) ** 2)))

            expr_1 = logsumexp(K_b) - logsumexp(beam_Ks[i - 1])
            expr_2 = logsumexp(beam_Ks[i + 1]) - logsumexp(K_b)
            if expr_1 < 0:
                c_1 = 0.01
            else:
                c_1 = 1.0
            if expr_2 < 0:
                c_2 = 0.01
            else:
                c_2 = 1.0

            # should be a vector of size nOfLayers in beam i
            res.append(c_1 * tmp - c_2 * tmp)

        # last beam
        y_B = beam_ybs[-1]
        z_B = np.array(self.struct.energyLayers[-1])

        K_B = beam_Ks[-1]
        tmp_last = (np.exp(K_B) / np.sum(np.exp(K_B))) * (z_B * self.factor * (1 - (np.tanh(self.factor * y_B) ** 2)))

        expr_last = np.log(np.sum(np.exp(K_B))) - np.log(np.sum(np.exp(beam_Ks[-2])))
        if expr_last < 0.:
            c_last = 0.01
        else:
            c_last = 1.0
        # should be a vector of size nOfLayers in last beam
        res.append(c_last * tmp_last)

        flat_res = [item for sublist in res for item in sublist]

        for layer in range(len(flat_res)):
            tmp = mb.repmat(flat_res[layer], 1, self.struct.nSpotsInLayer[layer])
            X = np.concatenate((X, tmp), axis=1)

        X = X.flatten()

        return X * self.gamma
