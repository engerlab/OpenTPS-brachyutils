# -*- coding: utf-8 -*-

r"""
The :mod:`pyOpti.acceleration` module implements acceleration schemes for
use with the :mod:`pyOpti.solvers`. Pass a given acceleration object as an
argument to your chosen solver during its initialization so that the solver can
use it.
Interface
---------
The :class:`accel` base class defines a common interface to all acceleration
schemes:
.. autosummary::
    accel.pre
    accel.update_step
    accel.update_sol
    accel.post
Acceleration schemes
--------------------
Then, derived classes implement various common acceleration schemes.
.. autosummary::
    dummy
    backtracking
    linesearch
"""

import copy
import logging

import numpy as np


class accel(object):
    r"""
    Defines the acceleration scheme object interface.
    This class defines the interface of an acceleration scheme object intended
    to be passed to a solver inheriting from
    :class:`pyOpti.solvers.solver`. It is intended to be a base class for
    standard acceleration schemes which will implement the required methods.
    It can also be instantiated by user code and dynamically modified for
    rapid testing. This class also defines the generic attributes of all
    acceleration scheme objects.
    """

    def __init__(self):
        pass

    def pre(self, functions, x0):
        """
        Pre-processing specific to the acceleration scheme.
        Gets called when :func:`pyOpti.solvers.solve` starts running.
        """
        self._pre(functions, x0)

    def _pre(self, functions, x0):
        raise NotImplementedError("Class user should define this method.")

    def update_step(self, solver, objective, niter):
        """
        Update the step size for the next iteration.
        Parameters
        ----------
        solver : pyOpti.solvers.solver
            Solver on which to act.
        objective : list of floats
            List of evaluations of the objective function since the beginning
            of the iterative process.
        niter : int
            Current iteration number.
        Returns
        -------
        float
            Updated step size.
        """
        return self._update_step(solver, objective, niter)

    def _update_step(self, solver, objective, niter):
        raise NotImplementedError("Class user should define this method.")

    def update_sol(self, solver, objective, niter):
        """
        Update the solution point for the next iteration.
        Parameters
        ----------
        solver : pyOpti.solvers.solver
            Solver on which to act.
        objective : list of floats
            List of evaluations of the objective function since the beginning
            of the iterative process.
        niter : int
            Current iteration number.
        Returns
        -------
        array_like
            Updated solution point.
        """
        return self._update_sol(solver, objective, niter)

    def _update_sol(self, solver, objective, niter):
        raise NotImplementedError("Class user should define this method.")

    def post(self):
        """
        Post-processing specific to the acceleration scheme.
        Mainly used to delete references added during initialization so that
        the garbage collector can free the memory. Gets called when
        :func:`pyOpti.solvers.solve` finishes running.
        """
        self._post()

    def _post(self):
        raise NotImplementedError("Class user should define this method.")


class dummy(accel):
    r"""
    Dummy acceleration scheme which does nothing.
    Used by default in most of the solvers. It simply returns unaltered the
    step size and solution point it receives.
    """

    def _pre(self, functions, x0):
        pass

    def _update_step(self, solver, objective, niter):
        return solver.step

    def _update_sol(self, solver, objective, niter):
        return solver.sol

    def _post(self):
        pass


# -----------------------------------------------------------------------------
# Stepsize optimizers
# -----------------------------------------------------------------------------

class linesearch(dummy):
    r"""
    Backtracking lines earch acceleration based on the Armijo–Goldstein condition,
    is a line search method to determine the amount to move along a given search direction.
    It starts withca relatively large estimate of the step size for movement along
    the search direction, and iteratively shrinking the step size (i.e., "backtracking")
    until a decrease of the objective function is observed that adequately corresponds
    to the decrease that is expected, based on the local gradient of the objective function.
    Parameters
    ----------
    c1 : float
        backtracking parameter
    c2 : float
        backtracking parameter
    eps : float
        (Optional) quit if norm of step produced is less than this
    """
    def __init__(self, c1=5e-5,c2=0.8,eps=1e-8, **kwargs):
        self.c1 = c1
        self.c2 = c2
        self.eps = eps
        super(linesearch, self).__init__(**kwargs)

    def _update_step(self, solver, objective, niter):
        # Save current state of the solver
        properties = copy.deepcopy(vars(solver))
        logging.debug('(Begin) solver properties: {}'.format(properties))
        # initialize some useful variables
        self.f = solver.smooth_funs[0]
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
            self.c2 = (self.c2+1)/2 # reduce the step modifier
            if 1-self.c2 < self.eps: break

          if step * len_p < self.eps:
            print('  Step is  too small, stop')
            break

        print('  Linesearch done (' + str(n) + ' iter)')
        return step

class backtracking(dummy):
    r"""
    Backtracking acceleration based on a local quadratic approximation of the
    smooth part of the objective.
    Parameters
    ----------
    eta : float
        A number between 0 and 1 representing the ratio of the geometric
        sequence formed by successive step sizes. In other words, it
        establishes the relation `step_new = eta * step_old`.
        Default is 0.5.
    Notes
    -----
    This is the backtracking strategy used in the original FISTA paper,
    :cite:`beck2009FISTA`.
    Examples
    --------
    >>> import numpy as np
    >>> from pyOpti import functions, solvers, acceleration
    >>> y = [4, 5, 6, 7]
    >>> x0 = np.zeros(len(y))
    >>> f1 = functions.norm_l1(y=y, lambda_=1.0)
    >>> f2 = functions.norm_l2(y=y, lambda_=0.8)
    >>> accel = acceleration.backtracking()
    >>> solver = solvers.forward_backward(accel=accel, step=10)
    >>> ret = solvers.solve([f1, f2], x0, solver, atol=1e-32, rtol=None)
    ... # doctest: +ELLIPSIS
    Solution found after ... iterations:
        objective function f(sol) = 0.000000e+00
        stopping criterion: ATOL
    >>> ret['sol']
    array([4., 5., 6., 7.])
    """

    def __init__(self, eta=0.5, **kwargs):
        if (eta > 1) or (eta <= 0):
            raise ValueError("eta must be between 0 and 1.")
        self.eta = eta
        super(backtracking, self).__init__(**kwargs)

    def _update_step(self, solver, objective, niter):
        """
        Notes
        -----
        TODO: For now we're recomputing gradients in order to evaluate the
        backtracking criterion. In the future, it might be interesting to
        think of some design changes so that this function has access to the
        gradients directly.
        Since the call to `solver._algo()` modifies the internal state of the
        solver itself, we need to store the solver's property values before
        doing backtracking, and then restore the solver's state after
        backtracking is done. This takes more memory, but it's the only way to
        guarantee that backtracking is performing on a fixed solver state.
        """
        # Save current state of the solver
        properties = copy.deepcopy(vars(solver))
        logging.debug('(Begin) solver properties: {}'.format(properties))

        # Initialize some useful variables
        fn = 0
        grad = np.zeros_like(properties['sol'])
        for f in solver.smooth_funs:
            fn += f.eval(properties['sol'])
            grad += f.grad(properties['sol'])
        step = properties['step']

        logging.debug('fn = {}'.format(fn))

        while True:
            # Run the solver with the current stepsize
            solver.step = step
            logging.debug('Current step: {}'.format(step))
            solver._algo()
            logging.debug(
                '(During) solver properties: {}'.format(vars(solver)))

            # Record results
            fp = np.sum([f.eval(solver.sol) for f in solver.smooth_funs])
            logging.debug('fp = {}'.format(fp))

            dot_prod = np.dot(solver.sol - properties['sol'], grad)
            logging.debug('dot_prod = {}'.format(dot_prod))

            norm_diff = np.sum((solver.sol - properties['sol'])**2)
            logging.debug('norm_diff = {}'.format(norm_diff))

            # Restore the previous state of the solver
            for key, val in properties.items():
                setattr(solver, key, copy.copy(val))
            logging.debug('(Reset) solver properties: {}'.format(vars(solver)))

            if (2. * step * (fp - fn - dot_prod) <= norm_diff):
                logging.debug('Break condition reached')
                break
            else:
                logging.debug('Decreasing step')
                step *= self.eta

        return step
