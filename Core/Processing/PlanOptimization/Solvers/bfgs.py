import numpy as np

from Core.Processing.PlanOptimization.Acceleration.linesearch import LineSearch
from Core.Processing.PlanOptimization.Solvers.gradientDescent import GradientDescent


class BFGS(GradientDescent):
    """
    Broyden–Fletcher–Goldfarb–Shanno algorithm.
    This algorithm solves unconstrained nonlinear optimization problems.
    The BFGS method belongs to quasi-Newton methods, a class of hill-climbing
    optimization techniques that seek a stationary point of a (preferably twice
    continuously differentiable) function.
    """

    def __init__(self, accel=LineSearch(), **kwargs):
        super(BFGS, self).__init__(accel=accel, **kwargs)

    def _pre(self, functions, x0):
        super(BFGS, self)._pre(functions, x0)
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
        self.Hk = (self.I - rho_k * np.outer(sk, yk)).dot(Hk).dot(self.I - rho_k * np.outer(yk, sk)) + rho_k * np.outer(
            sk, sk)

    def _post(self):
        pass
