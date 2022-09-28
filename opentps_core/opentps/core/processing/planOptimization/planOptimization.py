import logging
import math

import numpy as np
import scipy.sparse as sp

from opentps.core.processing.planOptimization.objectives.doseFidelity import DoseFidelity

try:
    import sparse_dot_mkl
    use_MKL = 1
except:
    use_MKL = 0

from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.processing.planOptimization.solvers import sparcling, \
    beamletFree
from opentps.core.processing.planOptimization.solvers import lp, bfgs, localSearch
from opentps.core.processing.planOptimization.solvers import mip, fista, gradientDescent
from opentps.core.processing.planOptimization import planPreprocessing

logger = logging.getLogger(__name__)


class PlanOptimizer:
    def __init__(self, plan:RTPlan, **kwargs):

        self.solver = bfgs.ScipyOpt('L-BFGS-B')
        self.plan = planPreprocessing.extendPlanLayers(plan)
        self.initPlan = plan
        self.opti_params = kwargs
        self.functions = []
        self.xSquared = True

    def initializeWeights(self):
        # Total Dose calculation
        totalDose = self.plan.planDesign.beamlets.toDoseImage().imageArray
        maxDose = np.max(totalDose)
        try:
            x0 = self.opti_params['init_weights']
        except KeyError:
            normFactor = self.plan.planDesign.objectives.targetPrescription / maxDose
            if self.xSquared:
                normFactor = math.sqrt(normFactor)
            x0 = normFactor * np.ones(self.plan.numberOfSpots, dtype=np.float32)

        return x0

    def initializeFidObjectiveFunction(self):
        # crop on ROI
        roiObjectives = np.zeros(len(self.plan.planDesign.objectives.fidObjList[0].maskVec)).astype(bool)
        roiRobustObjectives = np.zeros(len(self.plan.planDesign.objectives.fidObjList[0].maskVec)).astype(bool)
        robust = False
        for objective in self.plan.planDesign.objectives.fidObjList:
            if objective.robust:
                robust = True
                roiRobustObjectives = np.logical_or(roiRobustObjectives, objective.maskVec)
            else:
                roiObjectives = np.logical_or(roiObjectives, objective.maskVec)
        roiObjectives = np.logical_or(roiObjectives, roiRobustObjectives)

        if use_MKL == 1:
            beamletMatrix = sparse_dot_mkl.dot_product_mkl(
                sp.diags(roiObjectives.astype(np.float32), format='csc'), self.plan.planDesign.beamlets.toSparseMatrix())
        else:
            beamletMatrix = sp.csc_matrix.dot(sp.diags(roiObjectives.astype(np.float32), format='csc'),
                                              self.plan.planDesign.beamlets.toSparseMatrix())
        self.plan.planDesign.beamlets.setUnitaryBeamlets(beamletMatrix)

        if robust:
            for s in range(len(self.plan.planDesign.scenarios)):
                if use_MKL == 1:
                    beamletMatrix = sparse_dot_mkl.dot_product_mkl(
                        sp.diags(roiRobustObjectives.astype(np.float32), format='csc'),
                        self.plan.planDesign.scenarios[s].toSparseMatrix())
                else:
                    beamletMatrix = sp.csc_matrix.dot(
                        sp.diags(roiRobustObjectives.astype(np.float32), format='csc'),
                        self.plan.planDesign.scenarios[s].toSparseMatrix())
                self.plan.planDesign.scenarios[s].setUnitaryBeamlets(beamletMatrix)

        objectiveFunction = DoseFidelity(self.plan, self.xSquared)
        self.functions.append(objectiveFunction)

    def optimize(self):
        self.initializeFidObjectiveFunction()
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
        # Fonctionne pas car self.plan = copie du plan
        self.initPlan.planDesign.beamlets = self.plan.planDesign.beamlets
        if self.xSquared:
            self.initPlan.spotMUs = np.square(weights).astype(np.float32)
            self.initPlan.planDesign.beamlets.beamletWeights = np.square(weights).astype(np.float32)
        else:
            self.initPlan.spotMUs = weights.astype(np.float32)
            self.initPlan.planDesign.beamlets.beamletWeights = weights.astype(np.float32)

        totalDose = self.plan.planDesign.beamlets.toDoseImage()

        return weights, totalDose, cost


class IMPTPlanOptimizer(PlanOptimizer):
    def __init__(self, method, plan:RTPlan, **kwargs):
        super().__init__(plan, **kwargs)

        if method == 'Scipy-BFGS':
            self.solver = bfgs.ScipyOpt('BFGS', **kwargs)
        elif method == 'Scipy-LBFGS':
            self.solver = bfgs.ScipyOpt('L-BFGS-B', **kwargs)
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
            self.solver = lp.LP(self.plan, **kwargs)
        else:
            logger.error(
                'Method {} is not implemented. Pick among ["Scipy-lBFGS", "Gradient", "BFGS", "FISTA"]'.format(
                    self.method))


class ARCPTPlanOptimizer(PlanOptimizer):
    def __init__(self, method, plan, **kwargs):
        super(ARCPTPlanOptimizer, self).__init__(plan, **kwargs)
        if method == 'FISTA':
            self.solver = fista.FISTA()
        elif method == 'LS':
            self.solver = localSearch.LS()
        elif method == 'MIP':
            self.solver = mip.MIP(self.plan, **kwargs)
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
