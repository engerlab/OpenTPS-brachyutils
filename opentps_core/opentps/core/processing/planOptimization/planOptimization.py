import logging
import math
from typing import Iterable

import numpy as np
import scipy.sparse as sp

from opentps.core.processing.planOptimization.objectives.doseFidelity import DoseFidelity

try:
    import sparse_dot_mkl
    use_MKL = 0 # Currently deactivated on purpose because sparse_dot_mkl generates seg fault
except:
    use_MKL = 0

cupy_available = False
try:
    import cupy as cp
    import cupyx as cpx
    cupy_available = True
except:
    cupy_available = False
from opentps.core.data.plan._photonPlan import PhotonPlan
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.plan._protonPlan import ProtonPlan
from opentps.core.processing.planOptimization.solvers import sparcling, \
    beamletFree
from opentps.core.processing.planOptimization.solvers import scipyOpt, bfgs, localSearch
from opentps.core.processing.planOptimization.solvers import fista, gradientDescent
from opentps.core.processing.planOptimization import planPreprocessing
from scipy.sparse import csc_matrix
from opentps.core.data.images._doseImage import DoseImage


logger = logging.getLogger(__name__)

try:
    import sparse_dot_mkl
    sdm_available = True
except:
    sdm_available = False

try:
    import mkl as mkl
    mkl_available = True
except:
    mkl_available = False

try:
    import cupy as cp
    import cupyx as cpx
    cupy_available = True
except:
    cupy_available = False

class PlanOptimizer:
    """
    This class is used to optimize a plan.

    Attributes
    ----------
    plan : RTPlan
        The plan to optimize.
    opti_params : dict
        The optimization parameters.
    functions : list
        The list of functions to optimize.
    solver : Solver (default: scipyOpt.ScipyOpt('L-BFGS-B'))
        The solver to use. By default, no bounds are set. Machine delivery constraints can (and should) be enforced
        by setting the bounds.
    thresholdSpotRemoval : float
        The threshold weight below which spots are removed from the plan and beamlet matrix.
    xSquared : bool
        If True, the weights are squared. True by default to avoid negative weights.
    hardwareAcceleration : str
        The acceleration method. It can be one of the following:
        - 'GPU' : use the GPU for the optimization.
        - 'MKL' : use the MKL library for the optimization with the maximum number of threads available.
        - 'MKL-n' : use the MKL library for the optimization with n threads.
        - 'MKL-n-DEBUG' : use the MKL library for the optimization with n threads and the debug mode.
        - 'MKL-DEBUG' : use the MKL library for the optimization with the debug mode.

    """
    def __init__(self, plan:RTPlan, hardwareAcceleration:str=None, **kwargs):

        self.solver = scipyOpt.ScipyOpt('L-BFGS-B')
        
        if isinstance(plan, ProtonPlan):
            planPreprocessing.extendPlanLayers(plan)
        self.plan = plan
        self.opti_params = kwargs
        self.functions = []
        self._xSquared = True
        self.thresholdSpotRemoval = 1e-6 # remove all spots below this value after optimization from the plan and
        # beamlet matrix
        self.GPU_acceleration = False
        self.MKL_acceleration = False
        if hardwareAcceleration is not None:
            if hardwareAcceleration == 'GPU':
                self.use_GPU_acceleration()
            elif hardwareAcceleration[:3] == 'MKL':
                if hardwareAcceleration == 'MKL':
                    self.use_MKL_acceleration()
                else:
                    args = hardwareAcceleration.split('-')
                    if args[1].isdigit():
                        n_threads = int(args[1])
                        if len(args) > 2:
                            debug = args[2] == 'DEBUG'
                            self.use_MKL_acceleration(n_threads, debug=debug)
                        self.use_MKL_acceleration(n_threads)
                    elif args[1] == 'DEBUG':
                        self.use_MKL_acceleration(debug=True)
            else:
                logger.warning('Unknown hardware acceleration method. No hardware acceleration will be used')


    @property
    def xSquared(self):
        return self._xSquared

    @xSquared.setter
    def xSquared(self, x2):
        self._xSquared = x2

    def use_GPU_acceleration(self):
        """
        Enable the uses of the GPU via cupy and cupyx (both library need to be installed as well as CUDA).
        """
        if cupy_available:
            self.GPU_acceleration = True
            logger.info('cupy imported in planOptimization module')
            logger.info('abnormal used memory: {}'.format(cp.get_default_memory_pool().used_bytes()))
        else:
            logger.warning('Unable to import CUPY, please configure CUPY to enable GPU acceleration')
            logger.info('Regular optimization will be used instead')
            self.GPU_acceleration = False

    def stop_GPU_accelration(self):
        """
        stop the use of GPU acceleration
        """
        self.GPU_acceleration = False
        logger.info('GPU accelerations deactivated')

    def use_MKL_acceleration(self,n_threads=None,debug=False):
        """
        Enable the uses of the MKL library for the optimization

        Parameters
        ----------
        n_threads : int (default: None)
            The number of threads to use. If None, the number of threads is set to the maximum number of threads available.
        debug : bool (default: False)
            If True, the debug mode is activated in sparse_dot_mkl.
        """

        if not sdm_available:
            logger.warning('Unable to import sparse_dot_mkl, please install sparse_dot_mkl to enable MKL acceleration')
            logger.info('Regular optimization will be used instead')

        if mkl_available:
            vers = mkl.get_version()['MajorVersion']
            logger.info('MKL version: {}'.format(vers))
        if not mkl_available:
            logger.warning('Unable to import mkl, please install mkl-service and mkl to enable MKL acceleration as this might cause issues with MKL version')

        if sdm_available:
            if debug:
                logger.info('MKL acceleration activated with debug mode')
                sparse_dot_mkl.set_debug_mode(True)
            if n_threads is not None:
                sparse_dot_mkl.mkl_set_num_threads(n_threads)
                logger.info('MKL acceleration activated with {} threads'.format(n_threads))
            logger.info('CAUTION : MKL might not work on Unix systems')
            self.MKL_acceleration = True
            logger.info('MKL acceleration activated')

    def stop_MKL_acceleration(self):
        """
        stop the use of MKL acceleration
        """
        self.MKL_acceleration = False
        logger.info('MKL acceleration deactivated')


    def initializeWeights(self):
        """
        Initialize the weights.

        Returns
        -------
        x0 : numpy.ndarray
            The weights.
        """
        # Total Dose calculation
        totalDose = self.computeDose().imageArray 
        maxDose = np.max(totalDose)
        try:
            x0 = self.opti_params['init_weights']
            logger.info('Initial weights are given by user')
        except KeyError:
            if isinstance(self.plan.planDesign.objectives.targetPrescription,Iterable):
                normFactor = self.plan.planDesign.objectives.targetPrescription[0] / maxDose
            else:
                normFactor = self.plan.planDesign.objectives.targetPrescription / maxDose
            if self.xSquared:
                normFactor = math.sqrt(normFactor)
            x0 = normFactor * np.ones(self.plan.planDesign.beamlets.shape[1], dtype=np.float32)

        return x0

    def initializeFidObjectiveFunction(self):
        """
        Initialize the dose fidelity objective function.
        """
        self.plan.planDesign.setScoringParameters()

        # crop on ROI
        if self.plan.planDesign.ROI_cropping == True:
            roiObjectives = np.zeros(len(self.plan.planDesign.objectives.fidObjList[0].maskVec)).astype(bool)
            roiRobustObjectives = np.zeros(len(self.plan.planDesign.objectives.fidObjList[0].maskVec)).astype(bool)
        else : 
            roiObjectives = np.ones(len(self.plan.planDesign.objectives.fidObjList[0].maskVec)).astype(bool)
            roiRobustObjectives = np.ones(len(self.plan.planDesign.objectives.fidObjList[0].maskVec)).astype(bool)

        robust = False
        for objective in self.plan.planDesign.objectives.fidObjList:
            if objective.robust:
                robust = True
                roiRobustObjectives = np.logical_or(roiRobustObjectives, objective.maskVec)
            else:
                roiObjectives = np.logical_or(roiObjectives, objective.maskVec)
        roiObjectives = np.logical_or(roiObjectives, roiRobustObjectives)

        if self.MKL_acceleration :
            logger.info("Using MKL to create sparse beamlet matrix")
            beamletMatrix = sparse_dot_mkl.dot_product_mkl(
                sp.diags(roiObjectives.astype(np.float32), format='csc'), self.plan.planDesign.beamlets.toSparseMatrix())
        else:
            beamletMatrix = sp.csc_matrix.dot(sp.diags(roiObjectives.astype(np.float32), format='csc'),
                                              self.plan.planDesign.beamlets.toSparseMatrix())

        self.plan.planDesign.beamlets.setUnitaryBeamlets(beamletMatrix)

        if robust:
            for s in range(len(self.plan.planDesign.robustness.scenarios)):
                if self.MKL_acceleration:
                    print("Using MKL to create sparse beamlet matrix")
                    beamletMatrix = sparse_dot_mkl.dot_product_mkl(
                        sp.diags(roiRobustObjectives.astype(np.float32), format='csc'),
                        self.plan.planDesign.robustness.scenarios[s].toSparseMatrix())
                else:
                    beamletMatrix = sp.csc_matrix.dot(
                        sp.diags(roiRobustObjectives.astype(np.float32), format='csc'),
                        self.plan.planDesign.robustness.scenarios[s].toSparseMatrix())
                self.plan.planDesign.robustness.scenarios[s].setUnitaryBeamlets(beamletMatrix)

        objectiveFunction = DoseFidelity(self.plan, self.xSquared,self.GPU_acceleration,self.MKL_acceleration)
        self.functions.append(objectiveFunction)

    def computeDose(self):
        assert hasattr(self.plan, 'planDesign')
        assert hasattr(self.plan.planDesign.beamlets, '_sparseBeamlets')
        assert self.plan.planDesign.beamlets._sparseBeamlets is not None

        beamlets = self.plan.planDesign.beamlets
        
        if self.plan.radiationType == 'PROTON':
            weights = np.array(self.plan.spotMUs, dtype=np.float32)
        else :
            weights = np.array(self.plan.beamletMUs, dtype=np.float32)

        if self.MKL_acceleration:
            totalDose = sparse_dot_mkl.dot_product_mkl(beamlets._sparseBeamlets, weights) * self.plan.numberOfFractionsPlanned
        else:
            totalDose = csc_matrix.dot(beamlets._sparseBeamlets, weights) * self.plan.numberOfFractionsPlanned

        totalDose = np.reshape(totalDose, beamlets._gridSize, order='F')
        totalDose = np.flip(totalDose, 0)
        totalDose = np.flip(totalDose, 1)

        doseImage = DoseImage(imageArray=totalDose, origin=beamlets._origin, spacing=beamlets._spacing,
                              angles=beamlets._orientation)

        return doseImage

    def optimize(self):
        """
        Optimize the plan.

        Returns
        -------
        numpy.ndarray
            The optimized weights.
        numpy.ndarray
            The total dose.
        float
            The cost.
        """
        logger.info('Prepare optimization ...')
        if self.GPU_acceleration:
            logger.info('abnormal used memory: {}'.format(cp.get_default_memory_pool().used_bytes()))
        self.initializeFidObjectiveFunction()
        x0 = self.initializeWeights()

        try:
            bounds = self.opti_params['bounds']
            logger.info('Bounds are given by user')
        except:
            bounds = None

        # Optimization
        if bounds is not None:
            result = self.solver.solve(self.functions, x0, bounds=bounds)
        else:
            result = self.solver.solve(self.functions, x0)

        if self.GPU_acceleration:
            self.functions[0].unload_blGPU()
            cp._default_memory_pool.free_all_blocks()

        return self.postProcess(result)

    def postProcess(self, result):
        """
        Post-process the optimization result. !! The spots and the according weight bellow the thresholdSpotRemoval are removed from the plan and beamlet matrix !!
        The optimized weights are saved in self.plan.spotMUs
        
        Parameters
        ----------
        result : dict
            The optimization result.

        Returns
        -------
        numpy.ndarray
            The total dose.
        float
            The value of the objective function.
        """
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
            self.niter = 1

        logger.info(
            ' {} terminated in {} Iter, x = {}, f(x) = {}, time elapsed {}, time per iter {}'
                .format(self.solver.__class__.__name__, self.niter, self.weights, self.cost, self.time, self.time / self.niter))

        # unload scenario beamlets
        for s in range(len(self.plan.planDesign.robustness.scenarios)):
            if self.plan.planDesign.robustness.scenarios[0] != self.plan.planDesign.beamlets :
                self.plan.planDesign.robustness.scenarios[s].unload()

        # total dose
        logger.info("Total dose calculation ...")
        if self.xSquared:
            MUs = np.square(self.weights).astype(np.float32) / self.plan.numberOfFractionsPlanned
        else:
            MUs = self.weights.astype(np.float32) / self.plan.numberOfFractionsPlanned
        if isinstance(self.plan,ProtonPlan):
            self.plan.spotMUs = MUs
        elif isinstance(self.plan,PhotonPlan): 
            self.plan.beamletMUs = MUs
        MU_before_simplify = MUs.copy()
        self.plan.simplify(threshold=self.thresholdSpotRemoval) # remove spots below self.thresholdSpotRemoval
        
        if isinstance(self.plan,ProtonPlan):
            if self.plan.planDesign.beamlets.shape[1] != len(self.plan.spotMUs):
                # Beamlet matrix has not removed zero weight column
                ind_to_keep = MU_before_simplify > self.thresholdSpotRemoval
                assert np.sum(ind_to_keep) == len(self.plan.spotMUs)
                self.plan.planDesign.beamlets.setUnitaryBeamlets(self.plan.planDesign.beamlets._sparseBeamlets[:, ind_to_keep])
                self.plan.planDesign.beamlets._weights = self.plan.spotMUs
            else:
                self.plan.planDesign.beamlets._weights = self.plan.spotMUs
        elif isinstance(self.plan,PhotonPlan):        
            if self.plan.planDesign.beamlets.shape[1] != len(self.plan.beamletMUs):
                # Beamlet matrix has not removed zero weight column
                ind_to_keep = MU_before_simplify > self.thresholdSpotRemoval
                assert np.sum(ind_to_keep) == len(self.plan.beamletMUs)
                self.plan.planDesign.beamlets.setUnitaryBeamlets(self.plan.planDesign.beamlets._sparseBeamlets[:, ind_to_keep])
                self.plan.planDesign.beamlets._weights = self.plan.beamletMUs
            else:
                self.plan.planDesign.beamlets._weights = self.plan.beamletMUs
        totalDose = self.computeDose()
        logger.info('Optimization done.')

        return totalDose, self.cost

    def getConvergenceData(self, method):
        """
        Get the convergence data.

        Parameters
        ----------
        method : str
            The optimization method.

        Returns
        -------
        dict
            The convergence data.
        """
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


class IntensityModulationOptimizer(PlanOptimizer):
    """
    This class is used to optimize an Intensity Modulated Radiation/Proton Therapy (IMRT/IMPT). It inherits from PlanOptimizer.
    Attributes
    ----------
    method : str
        The optimization method. It can be one of the following:
        - 'Scipy_BFGS'
        - 'Scipy_L-BFGS-B'
        - 'Scipy_SLSQP'
        - 'Scipy_COBYLA'
        - 'Scipy_trust-constr
        - 'Gradient'
        - 'BFGS'
        - 'LBFGS'
        - 'FISTA'
        - 'LP'

    plan : RTPlan
        The plan to optimize.
    dict
        The optimization parameters, depending on the selected method.
    """
    def __init__(self, method, plan:RTPlan, hardwareAcceleration:str=None, **kwargs):
        super().__init__(plan, hardwareAcceleration, **kwargs)
        self.method = method
        if "Scipy" in self.method:
            algo = self.method.split('_')[1]
            self.solver = scipyOpt.ScipyOpt(algo, **kwargs)
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
                'Method {} is not implemented. Pick among ["Scipy_BFGS", "Scipy_L-BFGS-B", "Scipy_SLSQP", "Scipy_COBYLA", "Scipy_trust-constr", "Gradient", "BFGS", "LBFGS", "FISTA", "LP]'.format(
                    self.method))

    def getConvergenceData(self):
        """
        Get the convergence data.

        Returns
        -------
        dict
            The convergence data.
        """
        return super().getConvergenceData(self.method)


class BoundConstraintsOptimizer(PlanOptimizer):
    """
    This class is used to optimize a plan with bound constraints. It inherits from PlanOptimizer.

    Attributes
    ----------
    bounds : tuple (default: (0.02, 5))
        The bounds.
    plan : RTPlan
        The plan to optimize.
    dict
        The optimization parameters for the SciPy methods.
    """
    def __init__(self, plan: RTPlan, hardwareAcceleration:str=None, method='Scipy_L-BFGS-B', bounds=(0.02, 250), **kwargs):
        super().__init__(plan, hardwareAcceleration, **kwargs)
        self.bounds = bounds
        if method == 'Scipy_L-BFGS-B':
            self.method = method
            self.solver = scipyOpt.ScipyOpt('L-BFGS-B', **kwargs)
        else:
            raise NotImplementedError(f'Method {method} does not accept bound constraints')

    @property
    def xSquared(self):
        return False

    def formatBoundsForSolver(self, bounds=None):
        """
        Format the bounds for the solver with respect to the number of fractions.

        Parameters
        ----------
        bounds : tuple (default: None)
            The bounds. If None, the bounds are set to self.bounds.

        Returns
        -------
        list
            The formatted bounds.
        """
        if bounds is None:
            bounds = self.bounds
        bound_min = bounds[0] * self.plan.numberOfFractionsPlanned
        bound_max = bounds[1] * self.plan.numberOfFractionsPlanned
        return [(bound_min, bound_max)] * self.plan.planDesign.beamlets.shape[1]

    def optimize(self, nIterations=None):
        """
        Optimize the plan.

        Parameters
        ----------
        nIterations : tuple (default: None)
            The number of iterations for the first and second optimization. If None, the number of iterations is set to self.opti_params['maxit'] // 2 if first bound is 0,
            else it is set to self.opti_params['maxiter'].

        Returns
        -------
        numpy.ndarray
            The optimized weights.
        numpy.ndarray
            The total dose.
        float
            The cost.
        """
        self.initializeFidObjectiveFunction()
        x0 = self.initializeWeights()

        if self.bounds[0] == 0:
            result = self.solver.solve(self.functions, x0, bounds=self.formatBoundsForSolver(self.bounds), maxit=self.opti_params.get('maxiter', 1000))
        elif self.bounds[0] < 0:
            raise ValueError("Bounds cannot be negative")
        else:
            if nIterations is not None:
                nit1, nit2 = nIterations[0], nIterations[1]
            else:
                nit1 = self.opti_params.get('maxiter', 1000) // 2
                nit2 = self.opti_params.get('maxiter', 1000) // 2
            
            # First Optimization with lower bound = 0
            self.solver.params['maxiter'] = nit1
            result = self.solver.solve(self.functions, x0, bounds=self.formatBoundsForSolver((0, self.bounds[1])))
            x0 = np.array(result['sol'])
            ind_to_keep = np.full(x0.shape, False)
            ind_to_keep[x0 >= self.bounds[0]] = True
            x0 = x0[ind_to_keep]

            self.functions = [] # to avoid a beamlet copy with different size
            self.plan.planDesign.beamlets.setUnitaryBeamlets(self.plan.planDesign.beamlets._sparseBeamlets[:, ind_to_keep])
            objectiveFunction = DoseFidelity(self.plan, self.xSquared)
            self.functions.append(objectiveFunction)

            # second optimization with lower bound = self.bounds[0]
            self.solver.params['maxiter'] = nit2
            result = self.solver.solve(self.functions, x0, bounds=self.formatBoundsForSolver(self.bounds))
            result_weights = np.zeros(ind_to_keep.shape, dtype=np.float32) # reintroduce filtered spots at zero MU
            result_weights[ind_to_keep] = result['sol']
            result['sol'] = result_weights

            self.thresholdSpotRemoval = 1e-6 # zero spot MUs are removed in the postProcess with plan.simplify(self.thresholdSpotRemoval)

        return self.postProcess(result)

    def getConvergenceData(self):
        return super().getConvergenceData(self.method)


class ARCPTPlanOptimizer(PlanOptimizer):
    """
    This class is used to optimize an arc proton therapy plan (ARCPT). It inherits from PlanOptimizer.

    Attributes
    ----------
    method : str
        The optimization method. It can be one of the following:
        - 'FISTA'
        - 'LS'
        - 'MIP'
        - 'SPArcling'
    plan : RTPlan
        The plan to optimize.
    dict
        The optimization parameters, depending on the selected method.
    """
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