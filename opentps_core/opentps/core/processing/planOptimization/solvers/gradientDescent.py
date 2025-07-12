# Copyright (c) 2014, EPFL LTS2
# All rights reserved.
import logging
import numpy as np

from opentps.core.processing.planOptimization.solvers.solver import ConvexSolver

logger = logging.getLogger(__name__)


class GradientDescent(ConvexSolver):
    """
    class for gradient descent solver. Inherits from ConvexSolver.
    This part of the code comes from the EPFL LTS2 convex optimization toolbox.
    """

    def __init__(self, **kwargs):
        super(GradientDescent, self).__init__(**kwargs)

    def _pre(self, functions, x0):

        for f in functions:
            if 'GRAD' in f.cap(x0):
                self.smoothFuns.append(f)
            else:
                logger.error('{} requires each function to '
                             'implement grad().'.format(self.__class__.__name__))

        logger.info('minimizing {} smooth '
                    'functions.'.format(self.__class__.__name__, len(self.smoothFuns)))

    def _algo(self):
        grad = np.zeros_like(self.sol)
        for f in self.smoothFuns:
            grad += f.grad(self.sol)
        self.sol[:] -= self.step * grad

    def _post(self):
        pass
