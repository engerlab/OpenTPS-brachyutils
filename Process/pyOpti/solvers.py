# -*- coding: utf-8 -*-

r"""
The :mod:`pyOpti.solvers` module implements a solving function (which will
minimize your objective function) as well as common solvers.
Solving
-------
Call :func:`solve` to solve your convex optimization problem using your
instantiated solver and functions objects.
Interface
---------
The :class:`solver` base class defines a common interface to all solvers:
.. autosummary::
    solver.pre
    solver.algo
    solver.post
Solvers
-------
Then, derived classes implement various common solvers.
.. autosummary::
    gradient_descent
    bfgs
    l-bfgs
"""

import time

import numpy as np

from Process.pyOpti.functions import dummy
from . import acceleration


def solve(functions, x0, plan, solver=None, atol=None, dtol=None, rtol=None,
          xtol=None, maxit=200, verbosity='LOW', output = None):
    r"""
    Solve an optimization problem whose objective function is the sum of some
    convex functions.
    This function minimizes the objective function :math:`f(x) =
    \sum\limits_{k=0}^{k=K} f_k(x)`, i.e. solves
    :math:`\operatorname{arg\,min}\limits_x f(x)` for :math:`x \in
    \mathbb{R}^{n \times N}` where :math:`n` is the dimensionality of the data
    and :math:`N` the number of independent problems. It returns a dictionary
    with the found solution and some informations about the algorithm
    execution.
    Parameters
    ----------
    functions : list of objects
        A list of convex functions to minimize. These are objects who must
        implement the :meth:`pyOpti.functions.func.eval` method. The
        :meth:`pyOpti.functions.func.grad` and / or
        :meth:`pyOpti.functions.func.prox` methods are required by some
        solvers. Note also that some solvers can only handle two convex
        functions while others may handle more. Please refer to the
        documentation of the considered solver.
    x0 : array_like
        Starting point of the algorithm, :math:`x_0 \in \mathbb{R}^{n \times
        N}`. Note that if you pass a numpy array it will be modified in place
        during execution to save memory. It will then contain the solution. Be
        careful to pass data of the type (int, float32, float64) you want your
        computations to use.
    solver : solver class instance, optional
        The solver algorithm. It is an object who must inherit from
        :class:`pyOpti.solvers.solver` and implement the :meth:`_pre`,
        :meth:`_algo` and :meth:`_post` methods. If no solver object are
        provided, a standard one will be chosen given the number of convex
        function objects and their implemented methods.
    atol : float, optional
        The absolute tolerance stopping criterion. The algorithm stops when
        :math:`f(x^t) < atol` where :math:`f(x^t)` is the objective function at
        iteration :math:`t`. Default is None.
    dtol : float, optional
        Stop when the objective function is stable enough, i.e. when
        :math:`\left|f(x^t) - f(x^{t-1})\right| < dtol`. Default is None.
    rtol : float, optional
        The relative tolerance stopping criterion. The algorithm stops when
        :math:`\left|\frac{ f(x^t) - f(x^{t-1}) }{ f(x^t) }\right| < rtol`.
        Default is :math:`10^{-3}`.
    xtol : float, optional
        Stop when the variable is stable enough, i.e. when :math:`\frac{\|x^t -
        x^{t-1}\|_2}{\sqrt{n N}} < xtol`. Note that additional memory will be
        used to store :math:`x^{t-1}`. Default is None.
    maxit : int, optional
        The maximum number of iterations. Default is 200.
    verbosity : {'NONE', 'LOW', 'HIGH', 'ALL'}, optional
        The log level : ``'NONE'`` for no log, ``'LOW'`` for resume at
        convergence, ``'HIGH'`` for info at all solving steps, ``'ALL'`` for
        all possible outputs, including at each steps of the proximal operators
        computation. Default is ``'LOW'``.
    Returns
    -------
    sol : ndarray
        The problem solution.
    solver : str
        The used solver.
    crit : {'ATOL', 'DTOL', 'RTOL', 'XTOL', 'MAXIT'}
        The used stopping criterion. See above for definitions.
    niter : int
        The number of iterations.
    time : float
        The execution time in seconds.
    objective : ndarray
        The successive evaluations of the objective function at each iteration.
    Examples
    --------
    >>> import numpy as np
    >>> from pyOpti import functions, solvers
    Define a problem:
    >>> y = [4, 5, 6, 7]
    >>> f = functions.norm_l2(y=y)
    Solve it:
    >>> x0 = np.zeros(len(y))
    >>> ret = solvers.solve([f], x0, atol=1e-2, verbosity='ALL')
    INFO: Dummy objective function added.
    INFO: Selected solver: forward_backward
        norm_l2 evaluation: 1.260000e+02
        dummy evaluation: 0.000000e+00
    INFO: Forward-backward method
    Iteration 1 of forward_backward:
        norm_l2 evaluation: 1.400000e+01
        dummy evaluation: 0.000000e+00
        objective = 1.40e+01
    Iteration 2 of forward_backward:
        norm_l2 evaluation: 2.963739e-01
        dummy evaluation: 0.000000e+00
        objective = 2.96e-01
    Iteration 3 of forward_backward:
        norm_l2 evaluation: 7.902529e-02
        dummy evaluation: 0.000000e+00
        objective = 7.90e-02
    Iteration 4 of forward_backward:
        norm_l2 evaluation: 5.752265e-02
        dummy evaluation: 0.000000e+00
        objective = 5.75e-02
    Iteration 5 of forward_backward:
        norm_l2 evaluation: 5.142032e-03
        dummy evaluation: 0.000000e+00
        objective = 5.14e-03
    Solution found after 5 iterations:
        objective function f(sol) = 5.142032e-03
        stopping criterion: ATOL
    Verify the stopping criterion (should be smaller than atol=1e-2):
    >>> np.linalg.norm(ret['sol'] - y)**2  # doctest:+ELLIPSIS
    0.00514203...
    Show the solution (should be close to y w.r.t. the L2-norm measure):
    >>> ret['sol']
    array([4.02555301, 5.03194126, 6.03832952, 7.04471777])
    Show the used solver:
    >>> ret['solver']
    'forward_backward'
    Show some information about the convergence:
    >>> ret['crit']
    'ATOL'
    >>> ret['niter']
    5
    >>> ret['time']  # doctest:+SKIP
    0.0012578964233398438
    >>> ret['objective']  # doctest:+NORMALIZE_WHITESPACE,+ELLIPSIS
    [[126.0, 0], [13.99999999..., 0], [0.29637392..., 0], [0.07902528..., 0],
    [0.05752265..., 0], [0.00514203..., 0]]
    """


    if verbosity not in ['NONE', 'LOW', 'HIGH', 'ALL']:
        raise ValueError('Verbosity should be either NONE, LOW, HIGH or ALL.')

    # Add a second dummy convex function if only one function is provided.
    if len(functions) < 1:
        raise ValueError('At least 1 convex function should be provided.')
    elif len(functions) == 1:
        #if solver == bfgs() or solver == lbfgs():
        #    continue
        functions.append(dummy())
        if verbosity in ['LOW', 'HIGH', 'ALL']:
            print('INFO: Dummy objective function added.')

    # Choose a solver if none provided.
    if not solver:
        if len(functions) == 2:
            fb0 = 'GRAD' in functions[0].cap(x0) and \
                  'PROX' in functions[1].cap(x0)
            fb1 = 'GRAD' in functions[1].cap(x0) and \
                  'PROX' in functions[0].cap(x0)
            if fb0 or fb1:
                solver = forward_backward()  # Need one prox and 1 grad.
            else:
                raise ValueError('No suitable solver for the given functions.')
        elif len(functions) > 2:
            solver = generalized_forward_backward()
        if verbosity in ['LOW', 'HIGH', 'ALL']:
            name = solver.__class__.__name__
            print('INFO: Selected solver: {}'.format(name))

    # Set solver and functions verbosity.
    translation = {'ALL': 'HIGH', 'HIGH': 'HIGH', 'LOW': 'LOW', 'NONE': 'NONE'}
    solver.verbosity = translation[verbosity]
    translation = {'ALL': 'HIGH', 'HIGH': 'LOW', 'LOW': 'NONE', 'NONE': 'NONE'}
    functions_verbosity = []
    for f in functions:
        functions_verbosity.append(f.verbosity)
        f.verbosity = translation[verbosity]

    tstart = time.time()
    crit = None
    niter = 0
    objective = [[f.eval(x0) for f in functions]]
    weights = [x0]
    sparsities = [0.]
    irradTimes = [np.inf]
    rtol_only_zeros = True

    # Best iteration init
    bestIter = 0
    bestCost = objective[0][0]
    bestWeight = x0

    # Solver specific initialization.
    solver.pre(functions, x0)

    while not crit:

        niter += 1

        if xtol is not None:
            last_sol = np.array(solver.sol, copy=True)

        if verbosity in ['HIGH', 'ALL']:
            name = solver.__class__.__name__
            print('Iteration {} of {}:'.format(niter, name))

        # Solver iterative algorithm.
        solver.algo(objective, niter)

        objective.append([f.eval(solver.sol) for f in functions])
        weights.append(solver.sol)
        current = np.sum(objective[-1])
        last = np.sum(objective[-2])

        # Save results
        if output is not None:
            with open(output,'wb') as filename:
                np.save(filename,np.array([weights,objective], dtype=object))

        # Record best iteration
        if objective[niter][0] < bestCost:
          bestCost = objective[niter][0]
          bestIter = niter
          bestWeights = solver.sol


        # Verify stopping criteria.
        if atol is not None and current < atol:
            crit = 'ATOL'
        if dtol is not None and np.abs(current - last) < dtol:
            crit = 'DTOL'
        if rtol is not None:
            div = current  # Prevent division by 0.
            if div == 0:
                if verbosity in ['LOW', 'HIGH', 'ALL']:
                    print('WARNING: (rtol) objective function is equal to 0 !')
                if last != 0:
                    div = last
                else:
                    div = 1.0  # Result will be zero anyway.
            else:
                rtol_only_zeros = False
            relative = np.abs((current - last) / div)
            if relative < rtol and not rtol_only_zeros:
                crit = 'RTOL'
        if xtol is not None:
            err = np.linalg.norm(solver.sol - last_sol)
            err /= np.sqrt(last_sol.size)
            if err < xtol:
                crit = 'XTOL'
        if maxit is not None and niter >= maxit:
            crit = 'MAXIT'

        if verbosity in ['HIGH', 'ALL']:
            print('    objective = {:.2e}'.format(current))

    # Restore verbosity for functions. In case they are called outside solve().
    for k, f in enumerate(functions):
        f.verbosity = functions_verbosity[k]

    if verbosity in ['LOW', 'HIGH', 'ALL']:
        print('Solution found after {} iterations:'.format(niter))
        print('    objective function f(sol) = {:e}'.format(current))
        print('    stopping criterion: {}'.format(crit))
        print('Best Iteration # {} with f(x) = {}'.format(bestIter, bestCost))

    # Returned dictionary.
    result = {'sol':       solver.sol,
              'solver':    solver.__class__.__name__,  # algo for consistency ?
              'crit':      crit,
              'niter':     niter,
              'time':      time.time() - tstart,
              'objective': objective}

    # Solver specific post-processing (e.g. delete references).
    solver.post()

    return result


class solver:
    r"""
    Defines the solver object interface.
    This class defines the interface of a solver object intended to be passed
    to the :func:`pyOpti.solvers.solve` solving function. It is intended to
    be a base class for standard solvers which will implement the required
    methods. It can also be instantiated by user code and dynamically modified
    for rapid testing. This class also defines the generic attributes of all
    solver objects.
    Parameters
    ----------
    step : float
        The gradient-descent step-size. This parameter is bounded by 0 and
        :math:`\frac{2}{\beta}` where :math:`\beta` is the Lipschitz constant
        of the gradient of the smooth function (or a sum of smooth functions).
        Default is 1.
    accel : pyOpti.acceleration.accel
        User-defined object used to adaptively change the current step size
        and solution while the algorithm is running. Default is a dummy
        object that returns unchanged values.
    """

    def __init__(self, step=1., accel=None):
        if step < 0:
            raise ValueError('Step should be a positive number.')
        self.step = step
        self.accel = acceleration.dummy() if accel is None else accel

    def pre(self, functions, x0):
        """
        Solver-specific pre-processing. See parameters documentation in
        :func:`pyOpti.solvers.solve` documentation.
        Notes
        -----
        When preprocessing the functions, the solver should split them into
        two lists:
        * `self.smooth_funs`, for functions involved in gradient steps.
        * `self.non_smooth_funs`, for functions involved proximal steps.
        This way, any method that takes in the solver as argument, such as the
        methods in :class:`pyOpti.acceleration.accel`, can have some
        context as to how the solver is using the functions.
        """
        self.sol = np.asarray(x0)
        self.smooth_funs = []
        self.non_smooth_funs = []
        self._pre(functions, self.sol)
        self.accel.pre(functions, self.sol)

    def _pre(self, functions, x0):
        raise NotImplementedError("Class user should define this method.")

    def algo(self, objective, niter):
        """
        Call the solver iterative algorithm and the provided acceleration
        scheme. See parameters documentation in
        :func:`pyOpti.solvers.solve`
        Notes
        -----
        The method :meth:`self.accel.update_sol` is called before
        :meth:`self._algo` because the acceleration schemes usually involves
        some sort of averaging of previous solutions, which can add some
        unwanted artifacts on the output solution. With this ordering, we
        guarantee that the output of solver.algo is not corrupted by the
        acceleration scheme.
        Similarly, the method :meth:`self.accel.update_step` is called after
        :meth:`self._algo` to allow the step update procedure to act directly
        on the solution output by the underlying algorithm, and not on the
        intermediate solution output by the acceleration scheme in
        :meth:`self.accel.update_sol`.
        """
        self.step = self.accel.update_step(self, objective, niter)
        self._algo()
        self.sol[:] = self.accel.update_sol(self, objective, niter)

    def _algo(self):
        raise NotImplementedError("Class user should define this method.")

    def post(self):
        """
        Solver-specific post-processing. Mainly used to delete references added
        during initialization so that the garbage collector can free the
        memory. See parameters documentation in
        :func:`pyOpti.solvers.solve`.
        """
        self._post()
        self.accel.post()
        del self.sol, self.smooth_funs, self.non_smooth_funs

    def _post(self):
        raise NotImplementedError("Class user should define this method.")


class gradient_descent(solver):
    r"""
    Gradient descent algorithm.
    This algorithm solves optimization problems composed of the sum of
    any number of smooth functions.
    See generic attributes descriptions of the
    :class:`pyOpti.solvers.solver` base class.
    Notes
    -----
    This algorithm requires each function implement the
    :meth:`pyOpti.functions.func.grad` method.
    See :class:`pyOpti.acceleration.regularized_nonlinear` for a very
    efficient acceleration scheme for this method.
    Examples
    --------
    >>> import numpy as np
    >>> from pyOpti import functions, solvers
    >>> dim = 25
    >>> np.random.seed(0)
    >>> xstar = np.random.rand(dim)  # True solution
    >>> x0 = np.random.rand(dim)
    >>> x0 = xstar + 5*(x0 - xstar) / np.linalg.norm(x0 - xstar)
    >>> A = np.random.rand(dim, dim)
    >>> step = 1 / np.linalg.norm(np.dot(A.T, A))
    >>> f = functions.norm_l2(lambda_=0.5, A=A, y=np.dot(A, xstar))
    >>> fd = functions.dummy()
    >>> solver = solvers.gradient_descent(step=step)
    >>> params = {'rtol':0, 'maxit':14000, 'verbosity':'NONE'}
    >>> ret = solvers.solve([f, fd], x0, solver, **params)
    >>> pctdiff = 100 * np.sum((xstar - ret['sol'])**2) / np.sum(xstar**2)
    >>> print('Difference: {0:.1f}%'.format(pctdiff))
    Difference: 1.3%
    """

    def __init__(self, **kwargs):
        super(gradient_descent, self).__init__(**kwargs)

    def _pre(self, functions, x0):

        for f in functions:
            if 'GRAD' in f.cap(x0):
                self.smooth_funs.append(f)
            else:
                raise ValueError('{} requires each function to '
                                 'implement grad().'.format(self.__class__.__name__))

        if self.verbosity == 'HIGH':
            print('INFO: {} minimizing {} smooth '
                  'functions.'.format(self.__class__.__name__, len(self.smooth_funs)))

    def _algo(self):
        grad = np.zeros_like(self.sol)
        for f in self.smooth_funs:
            grad += f.grad(self.sol)
        self.sol[:] -= self.step * grad

    def _post(self):
        pass


class bfgs(gradient_descent):
    r"""
    Broyden–Fletcher–Goldfarb–Shanno algorithm.
    This algorithm solves unconstrained nonlinear optimization problems.
    The BFGS method belongs to quasi-Newton methods, a class of hill-climbing
    optimization techniques that seek a stationary point of a (preferably twice
    continuously differentiable) function.
    See generic attributes descriptions of the
    :class:`pyOpti.solvers.solver` base class.
    """
    def __init__(self, accel=acceleration.linesearch(), **kwargs):
        super(bfgs, self).__init__(accel=accel, **kwargs)

    def _pre(self, functions, x0):
        super(bfgs,self)._pre(functions,x0)
        self.f = functions[0]
        self.I = np.identity(x0.size)
        self.Hk = self.I
        self.pk = -self.Hk.dot(self.f.grad(x0))

    def _algo(self):

        # current
        xk = self.sol.copy()
        Hk = self.Hk

        # compute search direction
        self.pk = -Hk.dot(self.f.grad(self.sol))

        # update x
        self.sol[:] += self.step * self.pk

        # compute H_{k+1} by BFGS update
        sk = self.sol - xk
        yk = self.f.grad(self.sol) - self.f.grad(xk)
        rho_k = float(1.0 / yk.dot(sk))
        self.Hk = (self.I - rho_k * np.outer(sk, yk)).dot(Hk).dot(self.I - rho_k * np.outer(yk, sk)) + rho_k * np.outer(sk, sk)


    def _post(self):
        pass

class lbfgs(bfgs):
    r"""
    Limited-memory Broyden–Fletcher–Goldfarb–Shanno algorithm (L-BFGS).
    It approximates BFGS using a limited amount of computer memory.
    Like the original BFGS, L-BFGS uses an estimate of the inverse Hessian matrix
    to steer its search through variable space, but where BFGS stores a dense n × n
    approximation to the inverse Hessian (n being the number of variables in the problem),
    L-BFGS stores only a few vectors that represent the approximation implicitly
    """
    def __init__(self, m=10, accel=acceleration.linesearch(), **kwargs):
        super(bfgs, self).__init__(accel=accel, **kwargs)
        self.m = m

    def _pre(self, functions, x0):
        super(lbfgs,self)._pre(functions,x0)
        self.sks = []
        self.yks = []

    def _algo(self):
        # current
        xk = self.sol.copy()
        Hk = self.Hk
        # compute search direction
        self.pk = - self.getHg(Hk, self.f.grad(self.sol))
        # update x
        self.sol[:] += self.step * self.pk

        # define sk and yk for convenience
        sk = self.sol - xk
        yk = self.f.grad(self.sol) - self.f.grad(xk)

        self.sks.append(sk)
        self.yks.append(yk)
        if len(self.sks) > self.m:
            self.sks = self.sks[1:]
            self.yks = self.yks[1:]

    def getHg(self, H0,g):
        ''' This function returns the approximate inverse Hessian\
                multiplied by the gradient, H*g        '''
        m_t = len(self.sks)
        q = g
        a = np.zeros(m_t)
        b = np.zeros(m_t)
        for i in reversed(range(m_t)):
            s = self.sks[i]
            y = self.yks[i]
            rho_i = float(1.0 / y.T.dot(s))
            a[i] = rho_i * s.dot(q)
            q = q - a[i] * y

        z = H0.dot(q)

        for i in range(m_t):
            s = self.sks[i]
            y = self.yks[i]
            rho_i = float(1.0 / y.T.dot(s))
            b[i] = rho_i * y.dot(z)
            z = z + s * (a[i] - b[i])

        return z

    def _post(self):
        pass

