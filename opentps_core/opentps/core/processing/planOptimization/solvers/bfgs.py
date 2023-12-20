import json
import logging
import time
import numpy as np
import scipy.optimize
from scipy.optimize import Bounds

from opentps.core.processing.planOptimization.acceleration.linesearch import LineSearch
from opentps.core.processing.planOptimization.solvers.gradientDescent import GradientDescent

logger = logging.getLogger(__name__)


class ScipyOpt:
    """
    ScipyOpt is a wrapper for the scipy.optimize.minimize function.

    Attributes
    ----------
    meth : str (default: 'L-BFGS')
        The name of the scipy.optimize.minimize method to be used.
    Nfeval : int
        The number of function evaluations.
    params : dict
        The parameters for the scipy.optimize.minimize function.
        The paremeters are:
            ftol : float (default: 1e-06)
                Tolerance for termination by the change of the cost function.
            gtol : float (default: 1e-05)
                Tolerance for termination by the norm of the gradient.
            maxit : int (default: 1000)
                Maximum number of iterations.
            output : str (default: None)
                The name of the output file.
    name : str
        The name of the solver.
    """
    def __init__(self, meth='L-BFGS', **kwargs):
        self.meth = meth
        self.Nfeval = 1
        self.params = kwargs
        self.params['ftol'] = self.params.get('ftol', 1e-06)
        self.params['gtol'] = self.params.get('gtol', 1e-05)
        self.params['maxit'] = self.params.get('maxit', 1000)
        self.params['output'] = self.params.get('output', None)
        self.name = meth

    def solve(self, func, x0, bounds=None):
        """
        Solves the planOptimization problem using the scipy.optimize.minimize function.

        Parameters
        ----------
        func : list of functions
            The functions to be optimized.
        x0 : list
            The initial guess.
        bounds : list of Bounds (default: None)
            The bounds on the variables for scipy.optimize.minimize.

        Returns
        -------
        result : dict
            The result of the planOptimization.
            The keys are:
                sol : list
                    The solution.
                crit : str
                    The termination criterion.
                niter : int
                    The number of iterations.
                time : float
                    The time of the planOptimization.
                objective : list
                    The value of the objective function at each iteration.
        """
        def callbackF(Xi):
            logger.info('Iteration {} of Scipy-{}'.format(self.Nfeval, self.meth))
            logger.info('objective = {0:.6e}  '.format(func[0].eval(Xi)))
            cost.append(func[0].eval(Xi))
            self.Nfeval += 1

        startTime = time.time()

        cost = [func[0].eval(x0)]
        if 'GRAD' not in func[0].cap(x0):
            logger.error('{} requires the function to implement grad().'.format(self.__class__.__name__))
        res = scipy.optimize.minimize(func[0].eval, x0, method=self.meth, jac=func[0].grad, callback=callbackF,
                                      options={'disp': True, 'iprint': -1, 'maxiter': self.params['maxit'], 'ftol': self.params['ftol'], 'gtol': self.params['gtol']},
                                      bounds=bounds)

        result = {'sol': res.x.tolist(), 'crit': res.message, 'niter': res.nit, 'time': time.time() - startTime,
                  'objective': cost}

        if self.params['output'] is not None:
            with open(self.params['output'],'w') as f:
                json.dump(result, f)

        return result


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
