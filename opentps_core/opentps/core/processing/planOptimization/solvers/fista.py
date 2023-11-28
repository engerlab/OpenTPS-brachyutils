# Copyright (c) 2014, EPFL LTS2
# All rights reserved.

import logging

import numpy as np

from opentps.core.processing.planOptimization.acceleration.fistaAccel import FistaAccel
from opentps.core.processing.planOptimization.solvers.solver import ConvexSolver
from opentps.core.processing.planOptimization.objectives.projections import PositiveProj

logger = logging.getLogger(__name__)


class FISTA(ConvexSolver):
    """
    Fast Iterative Shrinkage-Thresholding Algorithm (FISTA) solver class for convex problems. Inherit from ConvexSolver.
    This part of the code comes from the EPFL LTS2 convex optimization toolbox.

    Attributes
    ----------
    meth : str (default: 'ForwardBackward')
        The name of the FISTA method to be used.
    indicator : Indicator (default: None)
        The indicator function.
    projection : Projection (default: None)
        The projection function.
    lambda_ : float (default: 1)
        The lambda parameter.
    z : ndarray
        The z variable.
    """
    def __init__(self, accel=FistaAccel(), indicator=None, lambda_=1, **kwargs):
        super().__init__(accel=accel, **kwargs)
        self.meth = ""
        self.indicator = indicator
        self.projection = PositiveProj()
        self.lambda_ = lambda_
        self.z = []

    def _pre(self, functions, x0):
        if len(functions) == 2:
            fb0 = 'GRAD' in functions[0].cap(x0) and \
                  'PROX' in functions[1].cap(x0)
            fb1 = 'GRAD' in functions[1].cap(x0) and \
                  'PROX' in functions[0].cap(x0)
            if fb0 or fb1:
                self.meth = "ForwardBackward"  # Need one prox and 1 grad.
                logger.info('Forward-backward method')
                if len(functions) != 2:
                    logger.error('Forward-backward requires two convex functions.')

                if 'PROX' in functions[0].cap(x0) and 'GRAD' in functions[1].cap(x0):
                    # To work with dummy as proximal
                    # self.smooth_funs.append(functions[0])
                    # self.non_smooth_funs.append(functions[1])
                    # Original config
                    self.smoothFuns.append(functions[1])
                    self.nonSmoothFuns.append(functions[0])
                elif 'PROX' in functions[1].cap(x0) and 'GRAD' in functions[0].cap(x0):
                    self.smoothFuns.append(functions[0])
                    self.nonSmoothFuns.append(functions[1])
                else:
                    logger.error('Forward-backward requires a function to '
                                 'implement prox() and the other grad().')
            else:
                logger.error('No suitable solver for the given functions.')
        elif len(functions) > 2:
            self.meth = "GeneralizedForwardBackward"
            if self.lambda_ <= 0 or self.lambda_ > 1:
                logger.error('Lambda is bounded by 0 and 1.')

            for f in functions:

                if 'GRAD' in f.cap(x0):
                    self.smoothFuns.append(f)
                elif 'PROX' in f.cap(x0):
                    self.nonSmoothFuns.append(f)
                    self.z.append(np.array(x0, copy=True))
                else:
                    logger.error('Generalized forward-backward requires each '
                                 'function to implement prox() or grad().')

            logger.info('Generalized forward-backward minimizing {} smooth '
                        'functions and {} non-smooth functions.'.format(
                len(self.smoothFuns), len(self.nonSmoothFuns)))
            pass

    def _algo(self):
        if self.meth == "ForwardBackward":
            self.solveForwardBackward()
        else:
            self.solveGeneralizedForwardBackward()

    def _post(self):
        del self.z

    def solveForwardBackward(self):
        """
        Forward-backward proximal splitting algorithm (ISTA and FISTA).
        Can be used for problems composed of the sum of a
        smooth and a non-smooth function.
        For details about the algorithm, see A. Beck and M. Teboulle,
        "A fast iterative shrinkage-thresholding algorithm for linear inverse problems",
        SIAM Journal on Imaging Sciences, vol. 2, no. 1, pp. 183–202, 2009.
        """

        # Forward step
        x = self.sol - self.step * self.smoothFuns[0].grad(self.sol)
        # Backward step
        self.sol[:] = self.nonSmoothFuns[0].prox(x, self.step)

    def solveGeneralizedForwardBackward(self):
        """
        Generalized forward-backward proximal splitting algorithm.
        Can be used for problems composed of the sum of any number of
        smooth and non-smooth functions.
        For details about the algorithm, see H. Raguet,
        "A Generalized Forward-Backward Splitting",
        SIAM Journal on Imaging Sciences, vol. 6, no. 13, pp 1199-1226, 2013.
        """

        # Smooth functions.
        grad = np.zeros_like(self.sol)
        for f in self.smoothFuns:
            grad += f.grad(self.sol)

        # Non-smooth functions.
        if not self.nonSmoothFuns:
            self.sol[:] -= self.step * grad  # Reduces to gradient descent.

        else:
            sol = np.zeros_like(self.sol)
            for i, g in enumerate(self.nonSmoothFuns):
                tmp = 2 * self.sol - self.z[i] - self.step * grad
                tmp[:] = g.prox(tmp, self.step * len(self.nonSmoothFuns))
                self.z[i] += self.lambda_ * (tmp - self.sol)
                sol += 1. * self.z[i] / len(self.nonSmoothFuns)
            self.sol[:] = sol