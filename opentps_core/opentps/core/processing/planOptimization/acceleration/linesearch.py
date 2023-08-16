# Copyright (c) 2014, EPFL LTS2
# All rights reserved.
import copy
import numpy as np
from opentps.core.processing.planOptimization.acceleration.baseAccel import Dummy
# -----------------------------------------------------------------------------
# Stepsize optimizers
# -----------------------------------------------------------------------------
import logging
logger = logging.getLogger(__name__)

class LineSearch(Dummy):
    """
    Backtracking lines earch acceleration based on the Armijo–Goldstein condition,
    is a line search method to determine the amount to move along a given search direction.
    It starts withca relatively large estimate of the step size for movement along
    the search direction, and iteratively shrinking the step size (i.e., "backtracking")
    until a decrease of the objective function is observed that adequately corresponds
    to the decrease that is expected, based on the local gradient of the objective function.
    Inheriting from Dummy. Code from EPFL LTS2 toolbox.

    Parameters
    ----------
    c1 : float
        backtracking parameter
    c2 : float
        backtracking parameter
    eps : float
        (Optional) quit if norm of step produced is less than this
    """
    def __init__(self, c1=1e-4, c2=0.8, eps=1e-4, **kwargs):
        self.c1 = c1
        self.c2 = c2
        self.eps = eps
        super(LineSearch, self).__init__(**kwargs)

    def _update_step(self, solver, objective, niter):
        # Save current state of the solver
        properties = copy.deepcopy(vars(solver))
        logger.debug('(Begin) solver properties: {}'.format(properties))
        # initialize some useful variables
        self.f = solver.smoothFuns[0]
        derphi = np.dot(self.f.grad(properties['sol']),solver.pk)
        step = 1.0
        n = 0
        fn = self.f.eval(properties['sol']+ step * solver.pk)
        flim = self.f.eval(properties['sol']) + self.c1 * step * derphi
        len_p = np.linalg.norm(solver.pk)

        #Loop until Armijo condition is satisfied
        while fn > flim:
          step *= self.c2
          n += 1
          fn1 = self.f.eval(solver.sol + step * solver.pk)
          if fn1 < fn:
            fn = fn1
          else: # we passed the minimum
            step /= self.c2
            self.c2 = (self.c2+1)/2 # reduce the step modifier
            if 1-self.c2 < 1e-4: break

          if step * len_p < self.eps or n>10:
            logger.debug('  Step is  too small, stop')
            break

        logger.debug('  Linesearch done (' + str(n) + ' iter)')
        return step