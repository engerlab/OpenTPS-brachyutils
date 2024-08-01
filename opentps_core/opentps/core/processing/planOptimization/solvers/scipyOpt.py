import time
import json
import logging
import scipy.optimize
from scipy.optimize import Bounds

logger = logging.getLogger(__name__)

class ScipyOpt:
    """
    ScipyOpt is a wrapper for the scipy.optimize.minimize function.

    Attributes
    ----------
    meth : str (default: 'L-BFGS-B')
        The name of the scipy.optimize.minimize method to be used.
        Current supported methods: BFGS,L-BFGS-B,COBYLA,SLSQP,trust-constr
    Nfeval : int
        The number of function evaluations.
    params : dict
        The parameters for the scipy.optimize.minimize function.
        The parameters are:
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
    def __init__(self, meth='L-BFGS-B', **kwargs):
        self.meth = meth
        self.Nfeval = 1
        self.params = kwargs # go to https://docs.scipy.org/doc/scipy/reference/optimize.html to see options for each solver
        self.params['output'] = self.params.get('output', None)
        self.name = meth

        # Define the method-specific supported options
        self.method_options = {
            'BFGS': ['disp', 'maxiter', 'gtol', 'norm', 'eps', 'return_all', 'finite_diff_rel_step', 'xrtol', 'c1', 'c2','hess_inv0'],
            'L-BFGS-B': ['disp', 'maxiter', 'ftol', 'gtol', 'eps', 'maxfun', 'maxcor', 'iprint', 'maxls','finite_diff_rel_step'],
            'COBYLA': ['disp', 'maxiter', 'catol','rhobeg', 'tol'],
            'SLSQP': ['disp', 'maxiter', 'ftol', 'eps','finite_diff_rel_step'],
            'trust-constr': ['disp', 'maxiter', 'gtol', 'xtol', 'barrier_tol', 'sparse_jacobian','initial_tr_radius','initial_constr_penalty','initial_barrier_parameter','initial_barrier_tolerance','factorization_method','finite_diff_rel_step','verbose']
        }

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
            The bounds on the variables for scipy.optimize.minimize. By default, no bounds are set.
            Machine delivery constraints can (and should) be enforced by setting the bounds.

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
        def callbackF(Xi,state=None): # trust-constr method expects 2 positional arguments
            logger.info('Iteration {} of Scipy-{}'.format(self.Nfeval, self.meth))
            logger.info('objective = {0:.6e}  '.format(func[0].eval(Xi)))
            cost.append(func[0].eval(Xi))
            self.Nfeval += 1

        startTime = time.time()

        cost = [func[0].eval(x0)]
        if 'GRAD' not in func[0].cap(x0):
            logger.error('{} requires the function to implement grad().'.format(self.__class__.__name__))
        else :
            pass
        
        options = {key: self.params[key] for key in self.method_options.get(self.meth, []) if key in self.params}

        res = scipy.optimize.minimize(func[0].eval, x0, method=self.meth, jac=func[0].grad, callback=callbackF,
                                      options=options, bounds=bounds)
        result = {'sol': res.x.tolist(), 'crit': res.message, 'niter': res.nit if hasattr(res, "nit") else 0, 'time': time.time() - startTime,
                  'objective': cost} 

        if self.params['output'] is not None:
            with open(self.params['output'],'w') as f:
                json.dump(result, f)

        return result