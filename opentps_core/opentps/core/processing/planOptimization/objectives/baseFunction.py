# Copyright (c) 2014, EPFL LTS2
# All rights reserved.
import logging
import numpy as np

logger = logging.getLogger(__name__)


class BaseFunc(object):
    """
    Function object interface
    The instanced objects are meant to be passed
    to the :func: "solver.solve" solving
    function
    """

    def __init__(self, **kwargs):
        pass

    def eval(self, x):
        """
        Function evaluation

        Parameters
        ----------
        x : array_like
            Point at which the function is evaluated

        Returns
        -------
        sol : float
            Function value at x
        """
        sol = self._eval(np.asarray(x))
        name = self.__class__.__name__
        logger.debug('    {} evaluation: {}'.format(name, sol))
        return sol

    def _eval(self, x):
        raise NotImplementedError("Class user should define this prox method.")

    def prox(self, x, T):
        """
        Function proximal operator

        Parameters
        ----------
        x : array_like
            Point at which the proximal operator is evaluated
        T : float
            Proximal operator parameter

        Returns
        -------
        sol : array_like
            Proximal operator value at x
        """
        return self._prox(np.asarray(x), T)

    def _prox(self, x, T):
        raise NotImplementedError("Class user should define this prox method.")

    def grad(self, x):
        """
        Function gradient

        Parameters
        ----------
        x : array_like
            Point at which the gradient is evaluated

        Returns
        -------
        sol : array_like
            Gradient value at x
        """
        return self._grad(np.asarray(x))

    def _grad(self, x):
        raise NotImplementedError("Class user should define this prox method.")

    def cap(self, x):
        """
        Test the capabilities of the function object

        Parameters
        ----------
        x : array_like
            Point at which the capabilities are tested

        Returns
        -------
        cap : list
            List of capabilities
        """
        cap = ['EVAL', 'GRAD', 'PROX']
        try:
            self.eval(x)
        except NotImplementedError:
            cap.remove('EVAL')
        try:
            self.grad(x)
        except NotImplementedError:
            cap.remove('GRAD')
        try:
            self.prox(x, 1)
        except NotImplementedError:
            cap.remove('PROX')
        return cap


class Dummy(BaseFunc):
    """
    Dummy function which returns 0 (eval, prox, grad)
    """

    def __init__(self, **kwargs):
        # Constructor takes keyword-only parameters to prevent user errors.
        super(Dummy, self).__init__(**kwargs)

    def _eval(self, x):
        return 0

    def _prox(self, x, T):
        return x

    def _grad(self, x):
        return np.zeros_like(x)
