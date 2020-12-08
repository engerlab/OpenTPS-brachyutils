# -*- coding: utf-8 -*-

r"""
The :mod:`pyunlocbox.functions` module implements an interface for solvers to
access the functions to be optimized as well as common objective functions.
Interface
---------
The :class:`func` base class defines a common interface to all functions:
.. autosummary::
    func.cap
    func.eval
    func.prox
    func.grad
"""


import numpy as np

class func(object):
    r"""
    This class defines the function object interface.
    It is intended to be a base class for standard functions which will
    implement the required methods. It can also be instantiated by user code
    and dynamically modified for rapid testing.  The instanced objects are
    meant to be passed to the :func:`pyunlocbox.solvers.solve` solving
    function.

    Examples
    --------
    Let's define a parabola as an example of the manual implementation of a
    function object :
    >>> from pyunlocbox import functions
    >>> f = functions.func()
    >>> f._eval = lambda x: x**2
    >>> f._grad = lambda x: 2*x
    >>> x = [1, 2, 3, 4]
    >>> f.eval(x)
    array([ 1,  4,  9, 16])
    >>> f.grad(x)
    array([2, 4, 6, 8])
    >>> f.cap(x)
    ['EVAL', 'GRAD']
    """

    def __init__(self, tol=1e-3,
                 maxit=200, **kwargs):

        self.tol = tol
        self.maxit = maxit

        # Should be initialized if called alone, updated by solve().
        self.verbosity = 'NONE'

    def eval(self, x):
        r"""
        Function evaluation.
        Parameters
        ----------
        x : array_like
            The evaluation point. If `x` is a matrix, the function gets
            evaluated for each column, as if it was a set of independent
            problems. Some functions, like the nuclear norm, are only defined
            on matrices.
        Returns
        -------
        z : float
            The objective function evaluated at `x`. If `x` is a matrix, the
            sum of the objectives is returned.
        Notes
        -----
        This method is required by the :func:`pyunlocbox.solvers.solve` solving
        function to evaluate the objective function. Each function class
        should therefore define it.
        """
        sol = self._eval(np.asarray(x))
        if self.verbosity in ['LOW', 'HIGH']:
            name = self.__class__.__name__
            print('    {} evaluation: {:e}'.format(name, sol))
        return sol

    def _eval(self, x):
        raise NotImplementedError("Class user should define this method.")

    def prox(self, x, T):
        r"""
        Function proximal operator.
        Parameters
        ----------
        x : array_like
            The evaluation point. If `x` is a matrix, the function gets
            evaluated for each column, as if it was a set of independent
            problems. Some functions, like the nuclear norm, are only defined
            on matrices.
        T : float
            The regularization parameter.
        Returns
        -------
        z : ndarray
            The proximal operator evaluated for each column of `x`.
        Notes
        -----
        The proximal operator is defined by
        :math:`\operatorname{prox}_{\gamma f}(x) = \operatorname{arg\,min}
        \limits_z \frac{1}{2} \|x-z\|_2^2 + \gamma f(z)`
        This method is required by some solvers.
        When the map A in the function construction is a tight frame
        (semi-orthogonal linear transformation), we can use property (x) of
        Table 10.1 in :cite:`combettes:2011iq` to compute the proximal
        operator of the composition of A with the base function. Whenever
        this is not the case, we have to resort to some iterative procedure,
        which may be very inefficient.
        """
        return self._prox(np.asarray(x), T)

    def _prox(self, x, T):
        raise NotImplementedError("Class user should define this method.")

    def grad(self, x):
        r"""
        Function gradient.
        Parameters
        ----------
        x : array_like
            The evaluation point. If `x` is a matrix, the function gets
            evaluated for each column, as if it was a set of independent
            problems. Some functions, like the nuclear norm, are only defined
            on matrices.
        Returns
        -------
        z : ndarray
            The objective function gradient evaluated for each column of `x`.
        Notes
        -----
        This method is required by some solvers.
        """
        return self._grad(np.asarray(x))

    def _grad(self, x):
        raise NotImplementedError("Class user should define this method.")

    def cap(self, x):
        r"""
        Test the capabilities of the function object.
        Parameters
        ----------
        x : array_like
            The evaluation point. Not really needed, but this function calls
            the methods of the object to test if they can properly execute
            without raising an exception. Therefore it needs some evaluation
            point with a consistent size.
        Returns
        -------
        cap : list of string
            A list of capabilities ('EVAL', 'GRAD', 'PROX').
        """
        tmp = self.verbosity
        self.verbosity = 'NONE'
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
        self.verbosity = tmp
        return cap


class dummy(func):
    r"""
    Dummy function (eval, prox, grad).
    This can be used as a second function object when there is only one
    function to minimize. It always evaluates as 0.
    Examples
    --------
    >>> from pyunlocbox import functions
    >>> f = functions.dummy()
    >>> x = [1, 2, 3, 4]
    >>> f.eval(x)
    0
    >>> f.prox(x, 1)
    array([1, 2, 3, 4])
    >>> f.grad(x)
    array([0, 0, 0, 0])
    """

    def __init__(self, **kwargs):
        # Constructor takes keyword-only parameters to prevent user errors.
        super(dummy, self).__init__(**kwargs)

    def _eval(self, x):
        return 0

    def _prox(self, x, T):
        return x

    def _grad(self, x):
        return np.zeros_like(x)
