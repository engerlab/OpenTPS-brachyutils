# Copyright (c) 2014, EPFL LTS2
# All rights reserved.
import numpy as np
import logging

logger = logging.getLogger(__name__)

from opentps.core.processing.planOptimization.acceleration.baseAccel import Dummy
from opentps.core.processing.planOptimization.acceleration.backtracking import Backtracking


class FistaAccel(Dummy):
    """
    acceleration scheme for forward-backward solvers. Inherit from Dummy.
    Code from EPFL LTS2 toolbox.

    Attributes
    ----------
    t : float
        Restart variable t
    """

    def __init__(self, **kwargs):
        self.t = 1.
        super(FistaAccel, self).__init__(**kwargs)

    def _pre(self, functions, x0):
        self.sol = np.array(x0, copy=True)

    def _update_sol(self, solver, objective, niter):
        self.t = 1. if (niter == 1) else self.t  # Restart variable t if needed
        t = (1. + np.sqrt(1. + 4. * self.t ** 2.)) / 2.
        y = solver.sol + ((self.t - 1) / t) * (solver.sol - self.sol)
        self.t = t
        self.sol[:] = solver.sol
        return y

    def _post(self):
        del self.sol


class FistaBacktracking(Backtracking, FistaAccel):
    """
    acceleration scheme with backtracking for forward-backward solvers.
    For details about the acceleration scheme and backtracking strategy, see A. Beck and M. Teboulle,
    "A fast iterative shrinkage-thresholding algorithm for linear inverse problems",
    SIAM Journal on Imaging Sciences, vol. 2, no. 1, pp. 183–202, 2009.
    Inherit from Backtracking and FistaAccel.
    Code from EPFL LTS2 toolbox.
    """

    def __init__(self, eta=0.5, **kwargs):
        Backtracking.__init__(self, eta=eta, **kwargs)
        FistaAccel.__init__(self, **kwargs)
