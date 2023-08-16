# Copyright (c) 2014, EPFL LTS2
# All rights reserved.
import copy
import logging

import numpy as np

from opentps.core.processing.planOptimization.acceleration.baseAccel import Dummy
logger = logging.getLogger(__name__)

class Backtracking(Dummy):
    """
    Backtracking based on a local quadratic approximation of the smooth
    part of the objective. This is the backtracking strategy used in the original FISTA paper.
    Input:
    eta: (float) A number between 0 and 1 representing the ratio of the geometric
        sequence formed by successive step sizes. In other words, it
        establishes the relation `step_new = eta * step_old`.
        Default is 0.5.
    Inherits from Dummy.
    Code from EPFL LTS2 toolbox.

    Attributes
    ----------
    eta : float
        A number between 0 and 1 representing the ratio of the geometric
        sequence formed by successive step sizes.
    """
    def __init__(self, eta=0.5, **kwargs):
        if (eta > 1) or (eta <= 0):
            logger.error("eta must be between 0 and 1.")
        self.eta = eta
        super(Backtracking, self).__init__(**kwargs)

    def _update_step(self, solver, objective, niter):
        # Save current state of the solver
        properties = copy.deepcopy(vars(solver))
        logger.debug('(Begin) solver properties: {}'.format(properties))

        # Initialize some useful variables
        fn = 0
        grad = np.zeros_like(properties['sol'])
        for f in solver.smoothFuns:
            fn += f.eval(properties['sol'])
            grad += f.grad(properties['sol'])
        step = properties['step']

        logger.debug('fn = {}'.format(fn))
        n = 0
        while True:
            # Run the solver with the current stepsize
            solver.step = step
            logger.debug('Current step: {}'.format(step))
            solver._algo()
            logger.debug(
                '(During) solver properties: {}'.format(vars(solver)))

            # Record results
            fp = np.sum([f.eval(solver.sol) for f in solver.smoothFuns])
            logger.debug('fp = {}'.format(fp))

            dot_prod = np.dot(solver.sol - properties['sol'], grad)
            logger.debug('dot_prod = {}'.format(dot_prod))

            norm_diff = np.sum((solver.sol - properties['sol'])**2)
            logger.debug('norm_diff = {}'.format(norm_diff))

            # Restore the previous state of the solver
            for key, val in properties.items():
                setattr(solver, key, copy.copy(val))
            logger.debug('(Reset) solver properties: {}'.format(vars(solver)))

            if \
                    (2. * step * (fp - fn - dot_prod) <= norm_diff) or n > 10:
                logger.debug('Break condition reached')
                break
            else:
                logger.debug('Decreasing step')
                step *= self.eta
                n += 1

        return step
