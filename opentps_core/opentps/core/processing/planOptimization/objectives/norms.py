# Copyright (c) 2014, EPFL LTS2
# All rights reserved.
import numpy as np
import numpy.linalg as la
import logging
from numbers import Number
import math

import scipy as sp

try:
    import sparse_dot_mkl
    use_MKL = False # Currently deactivated on purpose because sparse_dot_mkl generates seg fault
except:
    use_MKL = False

from opentps.core.processing.planOptimization import tools
from opentps.core.processing.planOptimization.objectives.baseFunction import BaseFunc

logger = logging.getLogger(__name__)


class Norm(BaseFunc):
    """
    Base class which defines the attributes of the `norm` objects. Inherit from BaseFunc.
    Code from EPFL LTS2 toolbox.

    Attributes
    ----------
    lambda_ : float (default: 1)
        Regularization parameter.
    """

    def __init__(self, lambda_=1, **kwargs):
        super(Norm, self).__init__(**kwargs)
        self.lambda_ = lambda_


class NormL1(Norm):
    """
    L1-norm (eval, prox). Inherits from Norm.
    Code from EPFL LTS2 toolbox.
    """

    def __init__(self, **kwargs):
        # Constructor takes keyword-only parameters to prevent user errors.
        super(NormL1, self).__init__(**kwargs)

    def _eval(self, x):
        return self.lambda_ * np.sum(np.abs(x))

    def _prox(self, x, T):
        gamma = self.lambda_ * T
        sol = np.sign(x) * np.maximum(0, np.abs(x) - gamma)
        return sol


class NormL2(Norm):
    """
    L2-norm (eval, prox, grad). Inherits from Norm.
    Code from EPFL LTS2 toolbox.
    """

    def __init__(self, **kwargs):
        # Constructor takes keyword-only parameters to prevent user errors.
        super(NormL2, self).__init__(**kwargs)

    def _eval(self, x):
        # euclidean norm
        return self.lambda_ * np.sqrt(np.sum(x ** 2))

    def _grad(self, x):
        return self.lambda_ * np.divide(x, self._eval(x))

    def _prox(self, x, T):
        # Attention c'est parce que ici T = step
        gamma = self.lambda_ * T
        X = np.maximum(1 - gamma / (np.sqrt(np.sum(x ** 2))), 0)
        return np.multiply(X, x)


class NormL21(Norm):
    """
    L2,1-norm (eval, prox) for matrix (list of lists in our case):
    Sum of the Euclidean norms of the columns (items) of the matrix (list)
    The proximal operator for reg*||w||_2 (not squared).
    source lasso. Inherit from Norm.
    Code from EPFL LTS2 toolbox.
    """

    def __init__(self, plan=None, scaleReg="group_size", oldRegularisation=False,
                 **kwargs):
        super(NormL21, self).__init__(**kwargs)
        self.plan = plan
        self.struct = tools.WeightStructure(self.plan)
        # liste de taille nSpots qui dit à quel layer appartient le spot en question
        self.groupsIds_ = np.concatenate([size * [i] for i, size in enumerate(self.struct.nSpotsInLayer)])
        # liste de taille nLayers qui reprend tous les weights et == true si actif dans la layer en question
        self.groups_ = [self.groupsIds_ == u for u in np.unique(self.groupsIds_) if u >= 0]
        self.scaleReg = scaleReg
        self.oldRegularisation = oldRegularisation
        targetMask = self.plan.objectives.fidObjList[0].maskVec
        targetIndices = np.array(targetMask).nonzero()[0]
        self.BLTarget = plan.beamlets.toSparseMatrix()[targetIndices, :]
        self.iter = 0

    def _eval(self, x):
        if self.iter % 10 == 0:
            self.groupRegVector_ = self._get_reg_vector(x, self.lambda_)
            groupRegVector_ = self.groupRegVector_
        else:
            groupRegVector_ = self.groupRegVector_
        regulariser = 0
        for group, reg in zip(self.groups_, groupRegVector_):
            regulariser += reg * la.norm(x[group])
        return regulariser

    def _prox(self, x, T):
        if self.iter % 10 == 0:
            self.groupRegVector = self._get_reg_vector(x, self.lambda_)
            groupRegVector = self.groupRegVector_
        else:
            groupRegVector = self.groupRegVector_
        if not self.oldRegularisation:
            groupRegVector = np.asarray(groupRegVector) * T
        self.iter += 1
        return self._group_l2_prox(x, groupRegVector, self.groups_)

    def _l2_prox(self, x, reg):
        """The proximal operator for reg*||w||_2 (not squared).
        """
        norm_x = la.norm(x)
        if norm_x == 0:
            return 0 * x
        return max(0, 1 - reg / norm_x) * x

    def _l21demi(self, X):
        """
        L2,1/2 norm
        """
        res = np.zeros(len(X))
        for col, layer in enumerate(X):
            res[col] = np.sqrt(np.sum(np.square(X[col])))
        total = math.sqrt(np.sum(res))
        return total

    def _group_l2_prox(self, x, regCoeffs, groups):
        """The proximal map for the specified groups of coefficients.
        """
        x = x.copy()

        for group, reg in zip(groups, regCoeffs):
            x[group] = self._l2_prox(x[group], reg)
        return x

    def _get_reg_strength(self, x1D, x, group, reg, energyWeight, index):
        """Get the regularisation coefficient for one group.
        """
        scale_reg = str(self.scaleReg).lower()
        if scale_reg == "group_size":
            scale = math.sqrt(group.sum())
        elif scale_reg == "none":
            scale = 1
        elif scale_reg == "inverse_group_size":
            scale = 1 / math.sqrt(group.sum())
        elif scale_reg == "active":
            scale = 1 / self.activeLayers[index]
        elif scale_reg == "summu":
            if self.sumMuInlayer(x, index) != 0:
                scale = 1. / (self.sumMuInlayer(x, index))
            else:
                scale = 1.
        elif scale_reg == "energy":
            if energyWeight == 0:
                scale = 0
            else:
                scale = 1 / energyWeight
        elif scale_reg == "wenbo":
            arrayWithOnes = np.ones(len(x1D[group]))
            if use_MKL:
                beamDoseTarget = sparse_dot_mkl.dot_product_mkl(self.BLTarget[:, group], arrayWithOnes.astype(np.float32))
            else:
                beamDoseTarget = sp.dot_product_mkl(self.BLTarget[:, group],
                                                                arrayWithOnes.astype(np.float32))
            scale = np.sqrt(la.norm(beamDoseTarget) / self.struct.nSpotsInLayer[index])
        else:
            logger.error(
                '``scale_reg`` must be equal to "group_size",'
                ' "inverse_group_size" or "summu"  or "none"'
            )
        return reg * scale

    def _get_reg_vector(self, x, reg):
        """Get the group-wise regularisation coefficients from ``reg``.
        """
        self.activeEnergies = self.struct.getListOfActiveEnergies(x)
        self.activeLayersInBeam = self.struct.getListOfActiveLayersInBeams(x)
        self.activeLayers = np.concatenate(
            [size * [item] for item, size in zip(self.activeLayersInBeam, self.struct.nLayersInBeam)])
        energiesWeight = tools.getEnergyWeights(self.activeEnergies)
        X = self.struct.getEnergyStructure(x)
        scale_reg = str(self.scaleReg).lower()
        if isinstance(reg, Number) and scale_reg != "l21demi":
            reg = [
                self._get_reg_strength(x, X, group, reg, energiesWeight[i], i) for i, group in enumerate(self.groups_)
            ]
        elif scale_reg == 'l21demi':
            scale = self._l21demi(X)
            reg = [reg * (1 / scale) for i, group in enumerate(self.groups_)]
        else:
            reg = list(reg)
        return reg

    def sumMuInlayer(self, X, index):
        MUSum = np.sum(X[index])
        return MUSum
