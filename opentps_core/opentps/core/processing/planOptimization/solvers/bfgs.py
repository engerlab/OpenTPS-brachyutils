import logging
import numpy as np

from opentps.core.processing.planOptimization.acceleration.linesearch import LineSearch
from opentps.core.processing.planOptimization.solvers.gradientDescent import GradientDescent

logger = logging.getLogger(__name__)

class BFGS(GradientDescent):
    """
    Broyden–Fletcher–Goldfarb–Shanno algorithm.
    This algorithm solves unconstrained nonlinear planOptimization problems.
    The BFGS method belongs to quasi-Newton methods, a class of hill-climbing
    planOptimization techniques that seek a stationary point of a (preferably twice
    continuously differentiable) function.
    """

    def __init__(self, accel=LineSearch(), **kwargs):
        super(BFGS, self).__init__(accel=accel, **kwargs)

    def _pre(self, functions, x0):
        super(BFGS, self)._pre(functions, x0)
        self.f = functions[0]
        self.indentity = np.identity(x0.size)
        self.hessiank = self.indentity
        self.pk = -self.hessiank.dot(self.f.grad(x0))

    def _algo(self):
        # current
        xk = self.sol.copy()
        hk = self.hessiank

        # compute search direction
        self.pk = -hk.dot(self.f.grad(self.sol))

        # update x
        self.sol[:] += self.step * self.pk

        # compute H_{k+1} by BFGS update
        sk = self.sol - xk
        yk = self.f.grad(self.sol) - self.f.grad(xk)
        rhok = float(1.0 / yk.dot(sk))
        self.hessiank = (self.indentity - rhok * np.outer(sk, yk)).dot(hk).dot(
            self.indentity - rhok * np.outer(yk, sk)) + rhok * np.outer(
            sk, sk)

    def _post(self):
        pass


class LBFGS(BFGS):
    """
    Limited-memory Broyden–Fletcher–Goldfarb–Shanno algorithm (L-BFGS).
    It approximates BFGS using a limited amount of computer memory.
    Like the original BFGS, L-BFGS uses an estimate of the inverse Hessian matrix
    to steer its search through variable space, but where BFGS stores a dense n × n
    approximation to the inverse Hessian (n being the number of variables in the problem),
    L-BFGS stores only a few vectors that represent the approximation implicitly
    """

    def __init__(self, m=10, accel=LineSearch(), **kwargs):
        super(LBFGS, self).__init__(accel=accel, **kwargs)
        self.m = m

    def _pre(self, functions, x0):
        super(LBFGS, self)._pre(functions, x0)
        self.sks = []
        self.yks = []

    def _algo(self):
        # current
        xk = self.sol.copy()
        hk = self.hessiank
        # compute search direction
        self.pk = - self.getHg(hk, self.f.grad(self.sol))
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

    def getHg(self, H0, g):
        """
        This function returns the approximate inverse Hessian\
        multiplied by the gradient, H*g

        Parameters
        ----------
        H0 : ndarray
            Initial guess for the inverse Hessian
        g : ndarray
            Gradient of the objective function
        """
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
