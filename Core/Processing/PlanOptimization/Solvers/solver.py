import logging
import time

import numpy as np
import Core.Processing.PlanOptimization.Functions.baseFunction as baseFunction
import Core.Processing.PlanOptimization.Acceleration.baseAccel as baseAccel

logger = logging.getLogger(__name__)


class ConvexSolver:
    """
    Solver object interface.
    The instanced objects are meant to be passed
    to the "pyOpti.solvers.solve` solving function
    """

    def __init__(self, step=1., accel=None):
        self.nonSmoothFuns = None
        self.smoothFuns = None
        self.sol = None
        if step < 0:
            logger.error('Step should be a positive number.')
        self.step = step
        self.accel = baseAccel.Dummy() if accel is None else accel

    def solve(self, functions, x0, **kwargs):
        """
        Solve an optimization problem whose objective function is the sum of some
        convex functions.
        Inputs:
        - functions: list of convex functions to minimize (objects must implement the "pyopti.functions.func.eval"
        and/or pyopti.functions.func.prox" methods, required by some solvers.
        - x0: initial weight vector
        - solver: solver class instance.If no solver object are provided, a standard one will be chosen
          given the number of convex function objects and their implemented methods.
        """
        params = kwargs

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

            if 'xtol' in params:
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
            if 'atol' in params and (not (params['atol'] is None)):
                if current < params['atol']:
                    crit = 'ATOL'
            if 'dtol' in params and (not (params['dtol'] is None)):
                if np.abs(current - last) < dtol:
                    crit = 'DTOL'
            if 'ftol' in params and (not (params['ftol'] is None)):
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
                if relative < params['ftol'] and not ftol_only_zeros:
                    crit = 'FTOL'
            if 'xtol' in params and (not (params['xtol'] is None)):
                err = np.linalg.norm(self.sol - last_sol)
                err /= np.sqrt(last_sol.size)
                if err < params['xtol']:
                    crit = 'XTOL'
            if 'maxit' in params:
                if niter >= params['maxit']:
                    crit = 'MAXIT'

            logger.info('    objective = {:.2e}'.format(current))

        logger.info('Solution found after {} iterations:'.format(niter))
        logger.info('    objective function f(sol) = {:e}'.format(current))
        logger.info('    stopping criterion: {}'.format(crit))
        logger.info('Best Iteration # {} with f(x) = {}'.format(bestIter, bestCost))

        # Returned dictionary.
        result = {'sol': solver.sol,
                  'solver': solver.__class__.__name__,
                  'crit': crit,
                  'niter': niter,
                  'time': time.time() - startTime,
                  'objective': objective}

        # Solver specific post-processing (e.g. delete references).
        self.post()

        return result

    def pre(self, functions, x0):
        """
        Solver-specific pre-processing;
        functions split in two lists:
        - self.smooth_funs : functions involved in gradient steps
        - self.non_smooth_funs : functions involved in proximal steps
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
