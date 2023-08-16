# Copyright (c) 2014, EPFL LTS2
# All rights reserved.
import logging

logger = logging.getLogger(__name__)


class Accel(object):
    """
    acceleration scheme object interface
    The instanced objects are meant to be passed
    to a solver inheriting from
    "pyOpti.solvers.solver"
    Code from EPFL LTS2 toolbox.
    """

    def __init__(self):
        pass

    def pre(self, functions, x0):
        """
        Pre-processing specific to the acceleration scheme.
        """
        self._pre(functions, x0)

    def _pre(self, functions, x0):
        logger.error("Class user should define this method.")

    def update_step(self, solver, objective, niter):
        """
        Update the step size for the next iteration

        Parameters
        ----------
        solver : Solver
            Solver on which to act.
        objective : list
            List of evaluations of the objective function since the beginning
            of the iterative process.
        niter : int
            Current iteration number.

        Returns
        -------
        step : float
            Updated step size.
        """
        return self._update_step(solver, objective, niter)

    def _update_step(self, solver, objective, niter):
        """
        Update the solution point for the next iteration.
        Inputs:
        - solver: Solver on which to act.
        - objective: List of evaluations of the objective function since the beginning
        of the iterative process.
        - niter: Current iteration number.
        Return updated solution point
        """

        logger.error("Class user should define this method.")

    def update_sol(self, solver, objective, niter):
        """
        Update the solution point for the next iteration.

        Parameters
        ----------
        solver : Solver
            Solver on which to act.
        objective : list
            List of evaluations of the objective function since the beginning
            of the iterative process.
        niter : int
            Current iteration number.

        Returns
        -------
        sol : array
            Updated solution point.
        """
        return self._update_sol(solver, objective, niter)

    def _update_sol(self, solver, objective, niter):
        logger.error("Class user should define this method.")

    def post(self):
        """
        Post-processing specific to the acceleration scheme.
        Mainly used to delete references added during initialization so that
        the garbage collector can free the memory.
        """

        self._post()

    def _post(self):
        logger.error("Class user should define this method.")


class Dummy(Accel):
    """
    Dummy acceleration scheme which does nothing. Inherit from Accel.
    """

    def _pre(self, functions, x0):
        logger.info('dummy accel')
        pass

    def _update_step(self, solver, objective, niter):
        return solver.step

    def _update_sol(self, solver, objective, niter):
        return solver.sol

    def _post(self):
        pass
