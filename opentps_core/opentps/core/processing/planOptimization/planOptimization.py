import logging
import math

import numpy as np
import scipy.sparse as sp

from opentps.core.processing.planOptimization.objectives.doseFidelity import DoseFidelity

try:
    import sparse_dot_mkl
    use_MKL = 0 # Currently deactivated on purpose because sparse_dot_mkl generates seg fault
except:
    use_MKL = 0

from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.processing.planOptimization.solvers import sparcling, \
    beamletFree
from opentps.core.processing.planOptimization.solvers import bfgs, localSearch
from opentps.core.processing.planOptimization.solvers import fista, gradientDescent
from opentps.core.processing.planOptimization import planPreprocessing

logger = logging.getLogger(__name__)


class PlanOptimizer:
    def __init__(self, plan:RTPlan, **kwargs):

        self.solver = bfgs.ScipyOpt('L-BFGS-B')
        planPreprocessing.extendPlanLayers(plan)
        self.plan = plan
        self.opti_params = kwargs
        self.functions = []
        self._xSquared = True
        self.thresholdSpotRemoval = 1e-6 # remove all spots below this value after optimization from the plan and beamlet matrix

    @property
    def xSquared(self):
        return self._xSquared

    @xSquared.setter
    def xSquared(self, x2):
        self._xSquared = x2


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
            x0 = normFactor * np.ones(self.plan.planDesign.beamlets.shape[1], dtype=np.float32)

        return x0

    def initializeFidObjectiveFunction(self):
        self.plan.planDesign.setScoringParameters()
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
            for s in range(len(self.plan.planDesign.robustness.scenarios)):
                if use_MKL == 1:
                    beamletMatrix = sparse_dot_mkl.dot_product_mkl(
                        sp.diags(roiRobustObjectives.astype(np.float32), format='csc'),
                        self.plan.planDesign.robustness.scenarios[s].toSparseMatrix())
                else:
                    beamletMatrix = sp.csc_matrix.dot(
                        sp.diags(roiRobustObjectives.astype(np.float32), format='csc'),
                        self.plan.planDesign.robustness.scenarios[s].toSparseMatrix())
                self.plan.planDesign.robustness.scenarios[s].setUnitaryBeamlets(beamletMatrix)

        objectiveFunction = DoseFidelity(self.plan, self.xSquared)
        self.functions.append(objectiveFunction)

    def optimize(self):
        logger.info('Prepare optimization ...')
        self.initializeFidObjectiveFunction()
        x0 = self.initializeWeights()
        # Optimization
        result = self.solver.solve(self.functions, x0)
        return self.postProcess(result)

    def postProcess(self, result):
        # Remove unnecessary attributs in plan
        try:
            del self.plan._spots
            del self.plan._layers
        except:
            pass

        self.weights = result['sol']
        crit = result['crit']
        self.niter = result['niter']
        self.time = result['time']
        self.cost = result['objective']

        if self.niter<=0:
            niter = 1

        logger.info(
            ' {} terminated in {} Iter, x = {}, f(x) = {}, time elapsed {}, time per iter {}'
                .format(self.solver.__class__.__name__, self.niter, self.weights, self.cost, self.time, self.time / self.niter))

        # unload scenario beamlets
        for s in range(len(self.plan.planDesign.robustness.scenarios)):
            self.plan.planDesign.robustness.scenarios[s].unload()

        # total dose
        logger.info("Total dose calculation ...")
        if self.xSquared:
            self.plan.spotMUs = np.square(self.weights).astype(np.float32)
        else:
            self.plan.spotMUs = self.weights.astype(np.float32)
        
        MU_before_simplify = self.plan.spotMUs.copy()
        self.plan.simplify(threshold=self.thresholdSpotRemoval) # remove spots below self.thresholdSpotRemoval
        if self.plan.planDesign.beamlets.shape[1] != len(self.plan.spotMUs):
            # Beamlet matrix has not removed zero weight column
            ind_to_keep = MU_before_simplify > self.thresholdSpotRemoval
            assert np.sum(ind_to_keep) == len(self.plan.spotMUs)
            self.plan.planDesign.beamlets.setUnitaryBeamlets(self.plan.planDesign.beamlets._sparseBeamlets[:, ind_to_keep])
            self.weights = np.array(self.weights)[ind_to_keep]
        self.plan.planDesign.beamlets.beamletWeights = self.plan.spotMUs

        totalDose = self.plan.planDesign.beamlets.toDoseImage()
        logger.info('Optimization done.')

        return self.weights, totalDose, self.cost

    def getConvergenceData(self, method):
        dct = {}
        if 'Scipy' in method:
            dct['func_0'] = self.cost[:-1]
        elif method == 'LP':
            raise NotImplementedError('No convergence data is available for LP')
        else:
            nFunctions = len(self.cost[0])
            for i in range(nFunctions):
                dct['func_%s' % i] = [itm[i] for itm in self.cost[:-1]]
        dct['time'] = self.time
        dct['nIter'] = self.niter

        return dct


class IMPTPlanOptimizer(PlanOptimizer):
    def __init__(self, method, plan:RTPlan, **kwargs):
        super().__init__(plan, **kwargs)
        self.method = method
        if self.method == 'Scipy-BFGS':
            self.solver = bfgs.ScipyOpt('BFGS', **kwargs)
        elif self.method == 'Scipy-LBFGS':
            self.solver = bfgs.ScipyOpt('L-BFGS-B', **kwargs)
        elif self.method == 'Gradient':
            self.solver = gradientDescent.GradientDescent(**kwargs)
        elif self.method == 'BFGS':
            self.solver = bfgs.BFGS(**kwargs)
        elif self.method == "LBFGS":
            self.solver = bfgs.LBFGS(**kwargs)
        elif self.method == "FISTA":
            self.solver = fista.FISTA(**kwargs)
        elif self.method == "LP":
            from opentps.core.processing.planOptimization.solvers import lp
            self.xSquared = False
            self.solver = lp.LP(self.plan, **kwargs)
        else:
            logger.error(
                'Method {} is not implemented. Pick among ["Scipy-LBFGS", "Gradient", "BFGS", "FISTA"]'.format(
                    self.method))

    def getConvergenceData(self):
        return super().getConvergenceData(self.method)


class BoundConstraintsOptimizer(PlanOptimizer):
    def __init__(self, plan:RTPlan, method='Scipy-LBFGS', bounds=(0.02, 5), **kwargs):
        super().__init__(plan, **kwargs)
        self.bounds = bounds
        if method == 'Scipy-LBFGS':
            self.solver = bfgs.ScipyOpt('L-BFGS-B', **kwargs)
        else:
            raise NotImplementedError(f'Method {method} does not accept bound constraints')

    @property
    def xSquared(self):
        return False

    def formatBoundsForSolver(self, bounds=None):
        if bounds is None:
            bounds = self.bounds
        bound_min = bounds[0] * self.plan.numberOfFractionsPlanned
        bound_max = bounds[1] * self.plan.numberOfFractionsPlanned
        return [(bound_min, bound_max)] * self.plan.planDesign.beamlets.shape[1]

    def optimize(self, nIterations=None):
        self.initializeFidObjectiveFunction()
        x0 = self.initializeWeights()

        if self.bounds[0] == 0:
            result = self.solver.solve(self.functions, x0, bounds=self.formatBoundsForSolver(self.bounds), maxit=self.opti_params.get('maxit', 1000))
        elif self.bounds[0] < 0:
            raise ValueError("Bounds cannot be negative")
        else:
            if nIterations is not None:
                nit1, nit2 = nIterations[0], nIterations[1]
            else:
                nit1 = self.opti_params.get('maxit', 1000) // 2
                nit2 = self.opti_params.get('maxit', 1000) // 2
            
            # First Optimization with lower bound = 0
            self.solver.params['maxit'] = nit1
            result = self.solver.solve(self.functions, x0, bounds=self.formatBoundsForSolver((0, self.bounds[1])))
            x0 = np.array(result['sol'])
            ind_to_keep = np.full(x0.shape,False)
            ind_to_keep[x0 >= self.bounds[0]] = True
            x0 = x0[ind_to_keep]
            self.functions = [] # to avoid a beamlet copy with different size
            self.plan.planDesign.beamlets.setUnitaryBeamlets(self.plan.planDesign.beamlets._sparseBeamlets[:, ind_to_keep])
            objectiveFunction = DoseFidelity(self.plan, self.xSquared)
            self.functions.append(objectiveFunction)

            # second optimization with lower bound = self.bounds[0]
            self.solver.params['maxit'] = nit2
            result = self.solver.solve(self.functions, x0, bounds=self.formatBoundsForSolver(self.bounds))
            result_weights = np.zeros(ind_to_keep.shape, dtype=np.float32) # reintroduce filtered spots at zero MU
            result_weights[ind_to_keep] = result['sol']
            result['sol'] = result_weights

            self.thresholdSpotRemoval = 1e-6 # zero spot MUs are removed in the postProcess with plan.simplify(self.thresholdSpotRemoval)

        return self.postProcess(result)
    


class ARCPTPlanOptimizer(PlanOptimizer):
    def __init__(self, method, plan, **kwargs):
        super(ARCPTPlanOptimizer, self).__init__(plan, **kwargs)
        if method == 'FISTA':
            self.solver = fista.FISTA()
        elif method == 'LS':
            self.solver = localSearch.LS()
        elif method == 'MIP':
            from opentps.core.processing.planOptimization.solvers import mip
            self.xSquared = False
            self.solver = mip.MIP(self.plan, **kwargs)
        elif method == 'SPArcling':
            try:
                mode = self.opti_params['mode']
                coreOptimizer = None
                if mode == "BLBased":
                    coreOptimizer = self.opti_params['core']
                self.solver = sparcling.SPArCling(mode, coreOptimizer)
            except KeyError:
                # Use default
                self.solver = sparcling.SPArCling()
        else:
            logger.error(
                'Method {} is not implemented. Pick among ["FISTA","LS","MIP","SPArcling"]'.format(self.method))
