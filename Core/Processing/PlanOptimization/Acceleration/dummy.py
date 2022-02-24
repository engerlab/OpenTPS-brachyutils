class Dummy(Accel):
    """
    Dummy acceleration scheme which does nothing.
    """

    def _pre(self, functions, x0):
        pass

    def _update_step(self, solver, objective, niter):
        return solver.step

    def _update_sol(self, solver, objective, niter):
        return solver.sol

    def _post(self):
        pass
