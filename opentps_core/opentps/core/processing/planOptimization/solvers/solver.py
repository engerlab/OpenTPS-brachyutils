# Copyright (c) 2014, EPFL LTS2
# All rights reserved.
import json
import logging
import time

import numpy as np
import opentps.core.processing.planOptimization.objectives.baseFunction as baseFunction
import opentps.core.processing.planOptimization.acceleration.baseAccel as baseAccel

logger = logging.getLogger(__name__)


class ConvexSolver(object):
    """
    ConvexSolver is the base class for all convex solvers.
    This part of the code comes from the EPFL LTS2 convex optimization toolbox.

    Attributes
    ----------
    step : float (default: 0.1)
        The step size.
    accel : Accel (default: None)
        The acceleration scheme.
    params : dict
        The parameters for the solver.
        The paremeters are:
            dtol : float (default: None)
                Tolerance for termination by the change of the cost function.
            xtol : float (default: None)
                Tolerance for termination by the change of the solution.
            atol : float (default: None)
                Tolerance for termination by the cost function.
            ftol : float (default: 1e-03)
                Tolerance for termination by the relative change of the cost function.
    non_smooth_funs : list
        The list of non-smooth functions.
    smooth_funs : list
        The list of smooth functions.
    fid_cost : list
        The list of the cost function values.
    sol : ndarray
        The solution.
    """

    def __init__(self, step=0.1, accel=None, **kwargs):
        self.nonSmoothFuns = []
        self.smoothFuns = []
        self.fidCost = []
        self.sol = None
        if step < 0:
            logger.error('Step should be a positive number.')
        self.step = step
        self.accel = baseAccel.Dummy() if accel is None else accel
        self.params = kwargs
        self.params['dtol'] = self.params.get('dtol', None)
        self.params['xtol'] = self.params.get('xtol', None)
        self.params['atol'] = self.params.get('atol', None)
        self.params['ftol'] = self.params.get('ftol', 1e-3)

    def solve(self, functions, x0):
        """
        Solve an planOptimization problem whose objective function is the sum of some
        convex functions.

        Parameters
        ----------
        functions : list
            list of convex functions to minimize (objects must implement the "pyopti.functions.func.eval"
            and/or pyopti.functions.func.prox methods, required by some solvers).
        x0 : ndarray
            initial weight vector

        Returns
        -------
        result : dict
            The result of the planOptimization.
            The keys are:
                sol : list
                    The solution.
                solver : str
                    The name of the solver.
                crit : str
                    The termination criterion.
                niter : int
                    The number of iterations.
                time : float
                    The time of the planOptimization.
                objective : list
                    The value of the objective function at each iteration.
        """

        # Add a second dummy convex function if only one function is provided.
        if len(functions) < 1:
            logger.error('At least 1 convex function should be provided.')
        elif len(functions) == 1:
            functions.append(baseFunction.Dummy())
            logger.info('Dummy objective function added')

        startTime = time.time()
        crit = None
        niter = 0
        objective = [[f.eval(x0) for f in functions]]
        weights = [x0.tolist()]
        ftol_only_zeros = True

        # Best iteration init
        bestIter = 0
        bestCost = objective[0][0]
        bestWeight = x0

        # Solver specific initialization.
        self.pre(functions, x0)

        while not crit:

            niter += 1

            if 'xtol' in self.params:
                last_sol = np.array(self.sol, copy=True)

            logger.info('Iteration {} of {}:'.format(niter, self.__class__.__name__))

            # Solver iterative algorithm.
            self.algo(objective, niter)

            objective.append([f.eval(self.sol) for f in functions])
            weights.append(self.sol.tolist())
            current = np.sum(objective[-1])
            last = np.sum(objective[-2])

            # Record best iteration
            if objective[niter][0] < bestCost:
                bestCost = objective[niter][0]
                bestIter = niter
                bestWeights = self.sol

            # Verify stopping criteria.
            if 'atol' in self.params and (not (self.params['atol'] is None)):
                if current < self.params['atol']:
                    crit = 'ATOL'
            if 'dtol' in self.params and (not (self.params['dtol'] is None)):
                if np.abs(current - last) < self.params['dtol']:
                    crit = 'DTOL'
            if 'ftol' in self.params and (not (self.params['ftol'] is None)):
                div = current  # Prevent division by 0.
                if div == 0:
                    logger.warning('WARNING: (ftol) objective function is equal to 0 !')
                    if last != 0:
                        div = last
                    else:
                        div = 1.0  # Result will be zero anyway.
                else:
                    ftol_only_zeros = False
                relative = np.abs((current - last) / div)
                if relative < self.params['ftol'] and not ftol_only_zeros:
                    crit = 'FTOL'
            if 'xtol' in self.params and (not (self.params['xtol'] is None)):
                err = np.linalg.norm(self.sol - last_sol)
                err /= np.sqrt(last_sol.size)
                if err < self.params['xtol']:
                    crit = 'XTOL'
            if 'maxiter' in self.params:
                if niter >= self.params['maxiter']:
                    crit = 'MAXITER'

            logger.info('    objective = {:.2e}'.format(current))

        logger.info('Solution found after {} iterations:'.format(niter))
        logger.info('    objective function f(sol) = {:e}'.format(current))
        logger.info('    stopping criterion: {}'.format(crit))
        logger.info('Best Iteration # {} with f(x) = {}'.format(bestIter, bestCost))

        # Returned dictionary.
        result = {'sol': self.sol.tolist(),
                  'solver': self.__class__.__name__,
                  'crit': crit,
                  'niter': niter,
                  'time': time.time() - startTime,
                  'objective': objective}

        if self.params.get('output') is not None:
            with open(self.params['output'], 'w') as f:
                json.dump(result, f)

        # Solver specific post-processing (e.g. delete references).
        self.post()

        return result

    def pre(self, functions, x0):
        """
        Solver-specific pre-processing;
        functions split in two lists:
        - self.smoothFuns : functions involved in gradient steps
        - self.nonSmoothFuns : functions involved in proximal steps

        Parameters
        ----------
        functions : list
            list of convex functions to minimize
        x0 : ndarray
            initial weight vector
        """
        self.sol = np.asarray(x0)
        self.smoothFuns = []
        self.nonSmoothFuns = []
        self._pre(functions, self.sol)
        self.accel.pre(functions, self.sol)

    def _pre(self, functions, x0):
        logging.error("Class user should define this method.")

    def algo(self, objective, niter):
        """
        Call the solver iterative algorithm and the provided acceleration
        scheme

        Parameters
        ----------
        objective : list
            The value of the objective function at each iteration.
        niter : int
            The number of iterations.
        """
        self.sol[:] = self.accel.update_sol(self, objective, niter)
        self.step = self.accel.update_step(self, objective, niter)
        self._algo()

    def _algo(self):
        logging.error("Class user should define this method.")

    def post(self):
        """
        Solver-specific post-processing. Mainly used to delete references added
        during initialization so that the garbage collector can free the
        memory.
        """
        self._post()
        self.accel.post()
        del self.sol, self.smoothFuns, self.nonSmoothFuns

    def _post(self):
        logging.error("Class user should define this method.")

    def objective(self, x):
        """
        Return the objective function at x.
        Necessitate `solver._pre(...)` to be run first.

        Parameters
        ----------
        x : ndarray
            The point at which the objective function is evaluated.

        Returns
        -------
        obj : list
            The value of the objective function at x.
        """
        return self._objective(x)

    def _objective(self, x):
        objSmooth = [f.eval(x) for f in self.smoothFuns]
        objNonsmooth = [f.eval(x) for f in self.nonSmoothFuns]
        return objNonsmooth + objSmooth
