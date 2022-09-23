import logging

import numpy as np
import scipy.sparse as sp

from Core.Data.Plan._planDesign import PlanDesign

try:
    import sparse_dot_mkl
    use_MKL = 1
except:
    use_MKL = 0

from Core.Data.Plan._rtPlan import RTPlan
from Core.Processing.PlanOptimization.Solvers import gradientDescent, bfgs, fista, localSearch, mip, sparcling, \
    beamletFree, lp
from Core.Processing.PlanOptimization import planPreprocessing

logger = logging.getLogger(__name__)


class PlanOptimizer:
    def __init__(self, plan:RTPlan, functions=None, **kwargs):
        if functions is None:
            functions = []
        self.solver = bfgs.ScipyOpt('L-BFGS-B')
        self.plan = planPreprocessing.extendPlanLayers(plan)
        self.initPlan = plan
        self.opti_params = kwargs
        self.functions = functions
        self.xSquared = True

    def initializeWeights(self):
        # Total Dose calculation
        weights = np.ones(self.plan.numberOfSpots, dtype=np.float32)

        if use_MKL == 1:
            totalDose = sparse_dot_mkl.dot_product_mkl(self.plan.planDesign.beamlets.toSparseMatrix(), weights)
        else:
            totalDose = sp.csc_matrix.dot(self.plan.planDesign.beamlets.toSparseMatrix(), weights)

        maxDose = np.max(totalDose)

        try:
            x0 = self.opti_params['init_weights']
        except KeyError:
            x0 = (self.plan.planDesign.objectives.targetPrescription / maxDose) * np.ones(self.plan.numberOfSpots,
                                                                           dtype=np.float32)
        if self.xSquared:
            x0 = np.sqrt(x0)

        return x0

    def optimize(self):
        x0 = self.initializeWeights()
        # Optimization
        result = self.solver.solve(self.functions, x0)
        return self.postProcess(result)

    def postProcess(self, result):
        weights = result['sol']
        crit = result['crit']
        niter = result['niter']
        time = result['time']
        cost = result['objective']

        if niter<=0:
            niter = 1

        logger.info(
            ' {} terminated in {} Iter, x = {}, f(x) = {}, time elapsed {}, time per iter {}'
                .format(self.solver.__class__.__name__, niter, weights, cost, time, time / niter))

        # unload scenario beamlets
        for s in range(len(self.plan.planDesign.scenarios)):
            self.plan.planDesign.scenarios[s].unload()

        # total dose
        logger.info("Total dose calculation ...")
        if self.xSquared:
            self.plan.spotMUs = np.square(weights).astype(np.float32)
            self.plan.planDesign.beamlets.beamletWeights = np.square(weights).astype(np.float32)
        else:
            self.plan.spotMUs = weights.astype(np.float32)
            self.plan.planDesign.beamlets.beamletWeights = weights.astype(np.float32)

        totalDose = self.plan.planDesign.beamlets.toDoseImage()

        return weights, totalDose, cost


class IMPTPlanOptimizer(PlanOptimizer):
    def __init__(self, method, plan:RTPlan, functions=None, **kwargs):
        super().__init__(plan, functions, **kwargs)
        if functions is None:
            logger.error('You must specify the function you want to optimize')
        if method == 'Scipy-BFGS':
            self.solver = bfgs.ScipyOpt('BFGS',**kwargs)
        elif method == 'Scipy-LBFGS':
            self.solver = bfgs.ScipyOpt('L-BFGS-B',**kwargs)
        elif method == 'Gradient':
            self.solver = gradientDescent.GradientDescent(**kwargs)
        elif method == 'BFGS':
            self.solver = bfgs.BFGS(**kwargs)
        elif method == "lBFGS":
            self.solver = bfgs.LBFGS(**kwargs)
        elif method == "FISTA":
            self.solver = fista.FISTA(**kwargs)
        elif method == "BLFree":
            self.solver = beamletFree.BLFree(**kwargs)
        elif method == "LP":
            self.solver = lp.LP(self.plan,**kwargs)
        else:
            logger.error(
                'Method {} is not implemented. Pick among ["Scipy-lBFGS", "Gradient", "BFGS", "FISTA"]'.format(
                    self.method))


class ARCPTPlanOptimizer(PlanOptimizer):
    def __init__(self, method, plan, functions=None, **kwargs):
        if functions is None:
            functions = []
        super(ARCPTPlanOptimizer, self).__init__(plan, functions, **kwargs)
        if method == 'FISTA':
            self.solver = fista.FISTA()
        elif method == 'LS':
            self.solver = localSearch.LS()
        elif method == 'MIP':
            self.solver = mip.MIP(self.plan,**kwargs)
        elif method == 'SPArcling':
            try:
                mode = self.params['mode']
                self.solver = sparcling.SPArCling(mode)
            except KeyError:
                # Use default
                self.solver = sparcling.SPArCling()
        else:
            logger.error(
                'Method {} is not implemented. Pick among ["FISTA","LS","MIP","SPArcling"]'.format(self.method))
