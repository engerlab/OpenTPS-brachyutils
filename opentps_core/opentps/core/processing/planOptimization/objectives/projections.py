# Copyright (c) 2014, EPFL LTS2
# All rights reserved.
import logging
from heapq import nsmallest

import numpy as np

from opentps.core.processing.planOptimization import tools
from opentps.core.processing.planOptimization.objectives.baseFunction import BaseFunc

logger = logging.getLogger(__name__)


class BaseProj(BaseFunc):
    """
    Base class which defines the attributes of the `proj` objects.
    Code from EPFL LTS2 toolbox.

    Attributes
    ----------
    epsilon : float (default: 1)
        Regularization parameter.
    method : str (default: 'FISTA')
        Method used to solve the proximal problem.
    """

    def __init__(self, epsilon=1, method='FISTA', **kwargs):
        super(BaseProj, self).__init__(**kwargs)
        self.epsilon = epsilon
        self.method = method

    def _eval(self, x):
        return 0


class PositiveProj(BaseProj):
    """
    Projection on nonnegative orthant (eval, prox)
    This function is the indicator function :math:`i_S(z)` of the set S which
    is zero if `z` is in the set and infinite otherwise. The set S is defined
    by \mathbb{R}^N_+ . Inherits from BaseProj.
    Code from EPFL LTS2 toolbox.
    """

    def __init__(self, **kwargs):
        # Constructor takes keyword-only parameters to prevent user errors.
        super(PositiveProj, self).__init__(**kwargs)

    def _prox(self, x, T):
        return np.clip(x, 0, np.inf)


class Indicator(BaseProj):
    """
    Projection on ? (eval, prox)
    Regularization function used to distribute
    the selected layers to the whole gantry rotating range.
    This function is the indicator function :math:`i_S(z)` of the set S which
    is zero if `z` is in the set and infinite otherwise. The set S is defined
    by ?
    ?: Indicator activated if beam MU <= epsilon. If yes, MU redistributed
    on activated layers for the sum to reach epsilon (esp= regularization parameter).
    Inherits from BaseProj.
    Code from EPFL LTS2 toolbox.

    Attributes
    ----------
    plan : Plan
        Plan object.
    smooth_fun : SmoothFunction
        Smooth function object.
    eps : float
        Regularization parameter.
    struct : WeightStructure
        Weight structure object.
    """

    def __init__(self, plan, smooth_fun, eps, **kwargs):
        super(Indicator, self).__init__(**kwargs)
        self.plan = plan
        self.eps = eps
        self.struct = tools.WeightStructure(self.plan)
        self.smooth_fun = smooth_fun

    def _prox(self, x, T):

        gxk = self.smooth_fun.grad(x)

        beamStruct = self.struct.nLayersInBeam
        energyStruct = self.struct.getEnergyStructure(x)
        g_energyStruct = self.struct.getEnergyStructure(gxk)
        X = []
        accumulateLayers = 0
        LayersReactivated = 0
        activeEnergyInBeams = []

        meanMUinbeams = []
        nOfMUinbeams = []
        i = 0

        for nOfLayers in beamStruct:
            # loop implicite sur les beams
            nOfMUInbeam = 0
            nOfWeightsInbeam = 0
            layersActiveInBeam = 0
            layersActiveInBeams = []
            LayersInbeam = []
            nOfWeightsInLayer = []
            meanGradientInLayer = []
            j = 0
            for el in range(len(energyStruct)):
                # loop sur les layers
                nOfMUInbeam += np.sum(energyStruct[accumulateLayers])
                nOfWeightsInbeam += len(energyStruct[accumulateLayers])
                LayersInbeam.append(energyStruct[accumulateLayers])
                nOfWeightsInLayer.append(len(energyStruct[accumulateLayers]))
                meanGradientInLayer.append(np.mean(g_energyStruct[accumulateLayers]))

                nOfMUInLayer = np.sum(energyStruct[accumulateLayers])
                if nOfMUInLayer > 0.:
                    # keep only last active energylayer in the beam
                    activeEnergyInBeams.append(self.struct.energyLayers[i][j])
                    layersActiveInBeams.append(el)
                    layersActiveInBeam += 1
                accumulateLayers += 1
                j += 1
                if len(LayersInbeam) == nOfLayers:
                    # reached number of Layers defined in beam, now next beam
                    break

            meanofMUInbeam = nOfMUInbeam / nOfLayers
            meanMUinbeams.append(meanofMUInbeam)
            nOfMUinbeams.append(nOfMUInbeam)
            # Condition to put in indicator function
            if nOfMUInbeam <= self.eps:
                missingMU = abs(self.eps - nOfMUInbeam)
                proj = LayersInbeam
                if layersActiveInBeam > 1:
                    MUdistributed = missingMU / layersActiveInBeam
                    FinalMUSUM = 0
                    initMUSUM = 0
                    for activeLayer in layersActiveInBeams:
                        initMUSUM += np.sum(proj[activeLayer])
                    for activeLayer in layersActiveInBeams:
                        proj[activeLayer] += (MUdistributed / len(proj[activeLayer]))
                        FinalMUSUM += sum(proj[activeLayer])
                else:
                    minGradLayers = nsmallest(4, meanGradientInLayer)
                    indexMinGradLayer1 = meanGradientInLayer.index(minGradLayers[0])
                    proj[indexMinGradLayer1] += (missingMU / len(proj[indexMinGradLayer1]))

                    # Si condition pas respectée , on ne fait rien
            else:
                proj = LayersInbeam

            # On concatene le tout ensemble pour un seul array par beam
            try:
                proj = np.concatenate(proj).ravel()
            except ValueError:
                pass
            # on ajoute l'array au vecteur final regroupant tous les beams
            X.append(proj)
            i += 1

        X = np.concatenate(X).ravel()
        return X
