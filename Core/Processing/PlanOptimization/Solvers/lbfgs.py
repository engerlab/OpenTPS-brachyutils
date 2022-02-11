import numpy as np

from Core.Processing.PlanOptimization.Acceleration.linesearch import LineSearch
from Core.Processing.PlanOptimization.Solvers.bfgs import BFGS


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

    def getHg(self, H0, g):
        """ This function returns the approximate inverse Hessian\
                multiplied by the gradient, H*g        """
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
