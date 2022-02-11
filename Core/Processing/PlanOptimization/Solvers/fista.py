import logging

from Core.Processing.PlanOptimization.Acceleration.accelFista import FISTA

logger = logging.getLogger(__name__)


class ForwardBackward(solver):
    """
    Forward-backward proximal splitting algorithm (ISTA and FISTA).
    Can be used for problems composed of the sum of a
    smooth and a non-smooth function.
    For details about the algorithm, see A. Beck and M. Teboulle,
    "A fast iterative shrinkage-thresholding algorithm for linear inverse problems",
    SIAM Journal on Imaging Sciences, vol. 2, no. 1, pp. 183–202, 2009.
    """

    def __init__(self, accel=FISTA(), indicator=None, **kwargs):
        super(ForwardBackward, self).__init__(accel=accel, **kwargs)
        self.indicator = indicator
        self.projection = proj_positive()

    def _pre(self, functions, x0):

        logger.info('Forward-backward method')

        if len(functions) != 2:
            logger.error('Forward-backward requires two convex functions.')

        if 'PROX' in functions[0].cap(x0) and 'GRAD' in functions[1].cap(x0):
            # To work with dummy as proximal
            # self.smooth_funs.append(functions[0])
            # self.non_smooth_funs.append(functions[1])
            # Original config
            self.smooth_funs.append(functions[1])
            self.non_smooth_funs.append(functions[0])
        elif 'PROX' in functions[1].cap(x0) and 'GRAD' in functions[0].cap(x0):
            self.smooth_funs.append(functions[0])
            self.non_smooth_funs.append(functions[1])
        else:
            logger.error('Forward-backward requires a function to '
                         'implement prox() and the other grad().')

    def _algo(self):
        # Forward step
        x_temp = self.sol - self.step * self.smooth_funs[0].grad(self.sol)
        # Positive projection
        x_temp_pos = self.projection.prox(x_temp, self.step)
        # Backward step
        x = self.non_smooth_funs[0].prox(x_temp_pos, self.step)
        # indicator step
        if self.indicator is not None:
            self.sol[:] = self.indicator._prox(x, self.smooth_funs[0].grad(x))
        else:
            self.sol[:] = x
        # self.sol[:] = x

    def _post(self):
        pass


class GeneralizedForwardBackward(solver):
    """
    Generalized forward-backward proximal splitting algorithm.
    Can be used for problems composed of the sum of any number of
    smooth and non-smooth functions.
    For details about the algorithm, see H. Raguet,
    "A Generalized Forward-Backward Splitting",
    SIAM Journal on Imaging Sciences, vol. 6, no. 13, pp 1199-1226, 2013.
    """

    def __init__(self, accel=acceleration.fista(), lambda_=1, indicator=None, **kwargs):
        super(generalized_forward_backward, self).__init__(accel=accel, **kwargs)
        self.lambda_ = lambda_
        self.projection = proj_positive()
        self.indicator = indicator

    def _pre(self, functions, x0):

        if self.lambda_ <= 0 or self.lambda_ > 1:
            logger.error('Lambda is bounded by 0 and 1.')

        self.z = []
        for f in functions:

            if 'GRAD' in f.cap(x0):
                self.smooth_funs.append(f)
            elif 'PROX' in f.cap(x0):
                self.non_smooth_funs.append(f)
                self.z.append(np.array(x0, copy=True))
            else:
                logger.error('Generalized forward-backward requires each '
                             'function to implement prox() or grad().')

        logger.info('Generalized forward-backward minimizing {} smooth '
                    'functions and {} non-smooth functions.'.format(
            len(self.smooth_funs), len(self.non_smooth_funs)))

    def _algo(self):

        # Smooth functions.
        grad = np.zeros_like(self.sol)
        for f in self.smooth_funs:
            grad += f.grad(self.sol)

        # Non-smooth functions.
        if not self.non_smooth_funs:
            self.sol[:] -= self.step * grad  # Reduces to gradient descent.

        else:
            '''sol = np.zeros(self.sol.shape)
            for i, g in enumerate(self.non_smooth_funs):
                tmp = 2 * self.sol - self.z[i] - self.step * grad
                tmp[:] = g.prox(tmp, self.step * len(self.non_smooth_funs))
                self.z[i] += self.lambda_ * (tmp - self.sol)
                sol += 1. * self.z[i] / len(self.non_smooth_funs)
            self.sol[:] = sol'''
            # Forward step
            x_temp = self.sol - self.step * grad
            # Positive projection
            x_temps_pos = self.projection.prox(x_temp, self.step)
            # Backward step
            x = self.non_smooth_funs[0].prox(x_temps_pos, self.step)

        # indicator step
        if self.indicator is not None:
            x = self.indicator._prox(x, self.smooth_funs[0].grad(x))
        self.sol[:] = x

    def _post(self):
        del self.z
