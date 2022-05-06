class Fista(Dummy):
    """
    Acceleration scheme for forward-backward solvers.
    """

    def __init__(self, **kwargs):
        self.t = 1.
        super(fista, self).__init__(**kwargs)

    def _pre(self, functions, x0):
        self.sol = np.array(x0, copy=True)

    def _update_sol(self, solver, objective, niter):
        self.t = 1. if (niter == 1) else self.t  # Restart variable t if needed
        t = (1. + np.sqrt(1. + 4. * self.t ** 2.)) / 2.
        y = solver.sol + ((self.t - 1) / t) * (solver.sol - self.sol)
        self.t = t
        self.sol[:] = solver.sol
        return y

    def _post(self):
        del self.sol


class FistaBacktracking(Backtracking, Fista):
    """
    Acceleration scheme with backtracking for forward-backward solvers.
    For details about the acceleration scheme and backtracking strategy, see A. Beck and M. Teboulle,
    "A fast iterative shrinkage-thresholding algorithm for linear inverse problems",
    SIAM Journal on Imaging Sciences, vol. 2, no. 1, pp. 183–202, 2009.
    """

    def __init__(self, eta=0.5, **kwargs):
        backtracking.__init__(self, eta=eta, **kwargs)
        fista.__init__(self, **kwargs)

