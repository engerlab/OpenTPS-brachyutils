import logging

import numpy as np
import scipy.sparse as sp

try:
    import sparse_dot_mkl

    use_MKL = 1
except:
    use_MKL = 0

from Core.Processing.PlanOptimization.Solvers import gradientDescent, bfgs, fista, localSearch, mip, sparcling, \
    beamletFree

logger = logging.getLogger(__name__)


class PlanOptimizer:
    def __init__(self, plan, contours, functions=None, opti_params=None, **kwargs):
        if functions is None:
            functions = []
        self.solver = bfgs.ScipyOpt('L-BFGS-B')
        self.plan = plan
        self.contours = contours
        self.opti_params = opti_params
        self.functions = functions

    def intializeWeights(self):
        # Total Dose calculation
        Weights = np.ones(self.plan.beamlets.NbrSpots, dtype=np.float32)
        if use_MKL == 1:
            TotalDose = sparse_dot_mkl.dot_product_mkl(self.plan.beamlets.BeamletMatrix, Weights)
        else:
            TotalDose = sp.csc_matrix.dot(self.plan.beamlets.BeamletMatrix, Weights)

        maxDose = np.max(TotalDose)
        try:
            x0 = self.opti_params['init_weights']
        except KeyError:
            x0 = (self.plan.Objectives.TargetPrescription / maxDose) * np.ones(self.plan.beamlets.NbrSpots,
                                                                               dtype=np.float32)
        return x0

    def optimize(self):
        # initialize objective function and weights
        # logger.info("Initialize objective function ...")
        # self.plan.Objectives.initialize_objective_function(self.contours)
        x0 = self.intializeWeights()
        # Optimization
        result = self.solver.solve(self.functions, x0, self.opti_params)
        self.postProcess(result)

    def postProcess(self, result):
        weights = result['sol']
        crit = result['crit']
        niter = result['niter']
        time = result['time']
        cost = result['objective']
        logger.info(
            ' {} terminated in {} Iter, x = {}, f(x) = {}, time elapsed {}, time per iter {}'
            .format(self.solver.__class__.__name__, niter, weights, cost, time, time / niter))

        # unload scenario beamlets
        for s in range(len(self.plan.scenarios)):
            self.plan.scenarios[s].unload()

        # total dose
        logger.info("Total dose calculation ...")
        self.plan.update_spot_weights(weights)
        totalDose = self.plan.beamlets.Compute_dose_from_beamlets(weights)

        return weights, totalDose, cost


class IMPTPlanOptimizer(PlanOptimizer):
    def __init__(self, method, plan, contours, functions=None, **kwargs):
        super().__init__(plan, contours, functions)
        if functions is None:
            logger.error('You must specify the function you want to optimize')
        self.method = method
        if self.method == 'Scipy-BFGS':
            self.solver = bfgs.ScipyOpt('BFGS')
        elif self.method == 'Scipy-LBFGS':
            self.solver = bfgs.ScipyOpt('L-BFGS-B')
        elif self.method == 'Gradient':
            self.solver = gradientDescent.GradientDescent()
        elif self.method == 'BFGS':
            self.solver = bfgs.BFGS()
        elif self.method == "lBFGS":
            self.solver = bfgs.LBFGS()
        elif self.method == "FISTA":
            self.solver = fista.FISTA()
        elif self.method == "BLFree":
            self.solver = beamletFree.BLFree()
        else:
            logger.error(
                'Method {} is not implemented. Pick among ["Scipy-lBFGS", "Gradient", "BFGS", "FISTA"]'.format(
                    self.method))

    def optimize(self):
        super(IMPTPlanOptimizer, self).optimize()


class ARCPTPlanOptimizer(PlanOptimizer):
    def __init__(self, method, plan, contours, functions=None, **kwargs):
        if functions is None:
            functions = []
        super(ARCPTPlanOptimizer, self).__init__(plan, contours, functions)
        self.method = method
        self.params = kwargs
        if self.method == 'FISTA':
            self.solver = fista.FISTA()
        elif self.method == 'LS':
            self.solver = localSearch.LS()
        elif self.method == 'MIP':
            self.solver = mip.MIP()
        elif self.method == 'SPArcling':
            try:
                mode = self.params['mode']
                self.solver = sparcling.SPArCling(mode)
            except KeyError:
                # Use default
                self.solver = sparcling.SPArCling()
        else:
            logger.error(
                'Method {} is not implemented. Pick among ["FISTA","LS","MIP","SPArcling"]'.format(self.method))

    def optimize(self):
        super(ARCPTPlanOptimizer, self).optimize()
