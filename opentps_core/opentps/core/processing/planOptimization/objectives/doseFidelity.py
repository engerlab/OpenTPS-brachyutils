import numpy as np
import scipy.sparse as sp
from copy import copy
import logging
logger = logging.getLogger(__name__)

try:
    import sparse_dot_mkl

    use_MKL = 0
except:
    use_MKL = 0

cupy_available = False
try:
    import cupy as cp
    import cupyx as cpx
    cupy_available = True
except:
    cupy_available = False

from opentps.core.processing.planOptimization.objectives.baseFunction import BaseFunc
from opentps.core.data._dvh import DVH


class DoseFidelity(BaseFunc):
    """
    Dose fidelity objective class. Inherits from BaseFunc.

    Attributes
    ----------
    list : list
        List of objectives
    xSquare : bool
        If true, the weights are squared. If false, the weights are not squared.
    beamlets : sparse matrix
        Beamlet matrix
    scenariosBL : list
        List of scenarios
    GPU_acceleration : bool (default: False)
        If true, the GPU is used for the computation of the fidelity function and gradient.
    """
    def __init__(self, plan, xSquare=True,GPU_acceleration=False):
        super(DoseFidelity, self).__init__()
        self.list = plan.planDesign.objectives.fidObjList
        self.xSquare = xSquare
        self.beamlets = plan.planDesign.beamlets.toSparseMatrix()
        self.GPU_acceleration = GPU_acceleration
        if GPU_acceleration:
            if cupy_available :
                logger.info('cupy imported and will be used in dosefidelity with version : {}'.format(cp.__version__))
                self.beamlets_gpu = cpx.scipy.sparse.csc_matrix(self.beamlets.astype(np.float32))
            else:
                self.GPU_acceleration = False
        if plan.planDesign.robustness.scenarios:
            self.scenariosBL = [plan.planDesign.robustness.scenarios[s].toSparseMatrix() for s in
                                range(len(plan.planDesign.robustness.scenarios))]
        else:
            self.scenariosBL = []

        self.savedWorstCase = (None, None)

    def unload_blGPU(self):
        del self.beamlets_gpu
        cp._default_memory_pool.free_all_blocks()


    def computeFidelityFunction(self, x, returnWorstCase=False):
        """
        Computes the fidelity function.

        Parameters
        ----------
        x : array
            Weights
        returnWorstCase : bool
            If true, the worst case scenario is returned. If false, the nominal scenario is returned.

        Returns
        -------
        fTot : float
            Fidelity function value
        worstCase : int (only if robust objectives are present)
            Worst case scenario index (-1 for nominal)
        """
        if self.xSquare:
            if self.GPU_acceleration:
                weights = cp.asarray(np.square(x).astype(np.float32))
            else:
                weights = np.square(x).astype(np.float32)
        else:
            if self.GPU_acceleration:
                weights = cp.asarray(x.astype(np.float32))
            else:
                weights = x.astype(np.float32)

        fTot = 0.0
        fTotScenario = 0.0
        scenarioList = []

        # compute objectives for nominal scenario
        if self.GPU_acceleration:
            doseTotal = cp.sparse.csc_matrix.dot(self.beamlets_gpu, weights)
        elif use_MKL == 1:
            doseTotal = sparse_dot_mkl.dot_product_mkl(self.beamlets, weights)
        else:
            doseTotal = sp.csc_matrix.dot(self.beamlets, weights)
        for objective in self.list:
            if objective.metric == objective.Metrics.DMAX:
                if self.GPU_acceleration:
                    f = np.mean(np.maximum(0, doseTotal[objective.maskVec].get() - objective.limitValue) ** 2)
                else:
                    f = np.mean(np.maximum(0, doseTotal[objective.maskVec] - objective.limitValue) ** 2)
            elif objective.metric == objective.Metrics.DMEAN:
                if self.GPU_acceleration:
                    f = np.maximum(0, np.mean(doseTotal[objective.maskVec].get(),
                                              dtype=np.float32) - objective.limitValue) ** 2
                else:
                    f = np.maximum(0,
                                   np.mean(doseTotal[objective.maskVec], dtype=np.float32) - objective.limitValue) ** 2
            elif objective.metric == objective.Metrics.DMIN:
                if self.GPU_acceleration:
                    f = np.mean(np.minimum(0, doseTotal[objective.maskVec].get() - objective.limitValue) ** 2)
                else:
                    f = np.mean(np.minimum(0, doseTotal[objective.maskVec] - objective.limitValue) ** 2)
            elif objective.metric == objective.Metrics.DUNIFORM:
                if self.GPU_acceleration:
                    f = np.mean((doseTotal[objective.maskVec].get() - objective.limitValue) ** 2)
                else:
                    f = np.mean((doseTotal[objective.maskVec] - objective.limitValue) ** 2)
            elif objective.metric == objective.Metrics.DFALLOFF:
                if self.GPU_acceleration:
                    f = np.mean(np.maximum(0, doseTotal[objective.maskVec].get() - objective.voxelwiseLimitValue) ** 2)
                else:
                    f = np.mean(np.maximum(0, doseTotal[objective.maskVec] - objective.voxelwiseLimitValue) ** 2)
            elif objective.metric == objective.Metrics.DVHMIN:
                if self.GPU_acceleration:
                    deviation = doseTotal[objective.maskVec].get() - objective.limitValue
                    DAV = self._calcInverseDVH(objective.volume, doseTotal[objective.maskVec]).get()
                    deviation[(doseTotal[objective.maskVec].get() > objective.limitValue) | (doseTotal[objective.maskVec].get() < DAV)] = 0
                    f = np.mean(deviation**2)
                else:
                    deviation = doseTotal[objective.maskVec] - objective.limitValue
                    DAV = self._calcInverseDVH(objective.volume, doseTotal[objective.maskVec])
                    deviation[(doseTotal[objective.maskVec] > objective.limitValue) | (doseTotal[objective.maskVec] < DAV)] = 0
                    f = np.mean(deviation**2)   
            elif objective.metric == objective.Metrics.DVHMAX:
                if self.GPU_acceleration:
                    deviation = doseTotal[objective.maskVec].get() - objective.limitValue
                    DAV = self._calcInverseDVH(objective.volume, doseTotal[objective.maskVec]).get()
                    deviation[(doseTotal[objective.maskVec].get() < objective.limitValue) | (doseTotal[objective.maskVec].get() > DAV)] = 0
                    f = np.mean(deviation**2)
                else:
                    deviation = doseTotal[objective.maskVec] - objective.limitValue
                    DAV = self._calcInverseDVH(objective.volume, doseTotal[objective.maskVec])
                    deviation[(doseTotal[objective.maskVec] < objective.limitValue) | (doseTotal[objective.maskVec] > DAV)] = 0
                    f = np.mean(deviation**2)
            elif objective.metric == objective.Metrics.EUDMAX:
                if self.GPU_acceleration:
                    DVH_a = np.mean(doseTotal[objective.maskVec].get() ** objective.EUDa) ** (1/objective.EUDa)
                    f = max(0, DVH_a - objective.limitValue) ** 2
                else:
                    DVH_a = np.mean(doseTotal[objective.maskVec] ** objective.EUDa) ** (1/objective.EUDa)
                    f = max(0, DVH_a - objective.limitValue) ** 2
            elif objective.metric == objective.Metrics.EUDMIN:
                if self.GPU_acceleration:
                    DVH_a = np.mean(doseTotal[objective.maskVec].get() ** objective.EUDa) ** (1/objective.EUDa)
                    f = min(0, DVH_a - objective.limitValue) ** 2
                else:
                    DVH_a = np.mean(doseTotal[objective.maskVec] ** objective.EUDa) ** (1/objective.EUDa)
                    f = min(0, DVH_a - objective.limitValue) ** 2
            elif objective.metric == objective.Metrics.EUDUNIFORM:
                if self.GPU_acceleration:
                    DVH_a = np.mean(doseTotal[objective.maskVec].get() ** objective.EUDa) ** (1/objective.EUDa)
                    f = (DVH_a - objective.limitValue) ** 2
                else:
                    DVH_a = np.mean(doseTotal[objective.maskVec] ** objective.EUDa) ** (1/objective.EUDa)
                    f = (DVH_a - objective.limitValue) ** 2   
            elif objective.metric == objective.Metrics.DFALLOFF:
                if self.GPU_acceleration:
                    f = np.mean(np.maximum(0, doseTotal[objective.maskVec].get() - objective.voxelwiseLimitValue) ** 2)
                else:
                    f = np.mean(np.maximum(0, doseTotal[objective.maskVec] - objective.voxelwiseLimitValue) ** 2)
            else:
                raise Exception(objective.metric + ' is not supported as an objective metric')
            if not objective.robust:
                #                if use_cupy: f = f.get() # transform into a scalar on CPU   #perhaps better to load all variables on gpu and then send back on cpu here at the end?

                fTot += objective.weight * f
            else:
                #                if use_cupy: f = f.get() # transform into a scalar on CPU

                fTotScenario += objective.weight * f

        if self.GPU_acceleration:  # try to prevent OOM error
            del weights, doseTotal
            cp._default_memory_pool.free_all_blocks()

        scenarioList.append(fTotScenario)

        # skip calculation of error scenarios if there is no robust objective
        robust = False
        for objective in self.list:
            if objective.robust:
                robust = True

        if self.scenariosBL == [] or robust is False:
            if not returnWorstCase:
                return fTot
            else:
                return fTot, -1  # returns id of the worst case scenario (-1 for nominal)

        # Compute objectives for error scenarios
        for ScenarioBL in self.scenariosBL:
            fTotScenario = 0.0

            if use_MKL == 1:
                doseTotal = sparse_dot_mkl.dot_product_mkl(ScenarioBL, weights)
            else:
                doseTotal = sp.csc_matrix.dot(ScenarioBL, weights)

            for objective in self.list:
                if not objective.robust:
                    continue

                if objective.metric == objective.Metrics.DMAX:
                    f = np.mean(np.maximum(0, doseTotal[objective.maskVec] - objective.limitValue) ** 2)
                elif objective.metric == objective.Metrics.DMEAN:
                    f = np.maximum(0,
                                   np.mean(doseTotal[objective.maskVec], dtype=np.float32) - objective.limitValue) ** 2
                elif objective.metric == objective.Metrics.DMIN:
                    f = np.mean(np.minimum(0, doseTotal[objective.maskVec] - objective.limitValue) ** 2)
                elif objective.metric == objective.Metrics.DUNIFORM:
                    f = np.mean((doseTotal[objective.maskVec] - objective.limitValue) ** 2)
                elif objective.metric == objective.Metrics.DFALLOFF:
                    f = np.mean(np.maximum(0, doseTotal[objective.maskVec] - objective.voxelwiseLimitValue) ** 2)
                elif objective.metric == objective.Metrics.DVHMIN:
                    deviation = doseTotal[objective.maskVec] - objective.limitValue
                    DAV = self._calcInverseDVH(objective.volume, doseTotal[objective.maskVec])
                    deviation[(doseTotal[objective.maskVec] > objective.limitValue) | (doseTotal[objective.maskVec] < DAV)] = 0
                    f = np.mean(deviation**2)
                elif objective.metric == objective.Metrics.DVHMAX:
                    deviation = doseTotal[objective.maskVec] - objective.limitValue
                    DAV = self._calcInverseDVH(objective.volume, doseTotal[objective.maskVec])
                    deviation[(doseTotal[objective.maskVec] < objective.limitValue) | (doseTotal[objective.maskVec] > DAV)] = 0
                    f = np.mean(deviation**2)
                elif objective.metric == objective.Metrics.EUDMAX:
                    DVH_a = np.mean(doseTotal[objective.maskVec] ** objective.EUDa) ** (1/objective.EUDa)
                    f = max(0, DVH_a - objective.limitValue) ** 2
                elif objective.metric == objective.Metrics.EUDMIN:
                    DVH_a = np.mean(doseTotal[objective.maskVec] ** objective.EUDa) ** (1/objective.EUDa)
                    f = min(0, DVH_a - objective.limitValue) ** 2
                elif objective.metric == objective.Metrics.EUDUNIFORM:
                    DVH_a = np.mean(doseTotal[objective.maskVec] ** objective.EUDa) ** (1/objective.EUDa)
                    f = (DVH_a - objective.limitValue) ** 2
                elif objective.metric == objective.Metrics.DFALLOFF:
                    f = np.mean(np.maximum(0, doseTotal[objective.maskVec] - objective.voxelwiseLimitValue) ** 2)
                else:
                    raise Exception(objective.metric + ' is not supported as an objective metric')

                fTotScenario += objective.weight * f

            scenarioList.append(fTotScenario)

        fTot += max(scenarioList)

        worstCaseIndex = scenarioList.index(max(scenarioList)) - 1  # returns id of the worst case scenario (-1 for nominal)
        self.savedWorstCase = (copy(x), worstCaseIndex)

        if not returnWorstCase:
            return fTot
        else:
            return fTot, worstCaseIndex

    def computeFidelityGradient(self, x):
        """
        Computes the fidelity gradient.

        Parameters
        ----------
        x : array
            Weights

        Returns
        -------
        dfTot : array
            Fidelity gradient

        Raises
        ------
        Exception
            If the objective metric is not supported.
        """
        # get worst case scenario
        if len(self.scenariosBL) > 0:
            if np.array_equal(x, self.savedWorstCase[0]):
                worstCase = self.savedWorstCase[1]
            else:
                _, worstCase = self.computeFidelityFunction(x, returnWorstCase=True)
        else:
            worstCase = -1
        if self.xSquare:
            if self.GPU_acceleration:
                weights = cp.asarray(np.square(x).astype(np.float32))
            else:
                weights = np.square(x).astype(np.float32)
        else:
            if self.GPU_acceleration:
                weights = cp.asarray(x.astype(np.float32))
            else:
                weights = x.astype(np.float32)

        if self.GPU_acceleration:
            xDiag = cpx.scipy.sparse.diags(x.astype(np.float32), format='csc')
        else:
            xDiag = sp.diags(x.astype(np.float32), format='csc')

        if self.GPU_acceleration:
            doseNominal = cp.sparse.csc_matrix.dot(self.beamlets_gpu, weights)
            if self.xSquare:
                doseNominalBL = cp.sparse.csc_matrix.dot(self.beamlets_gpu, xDiag)
            else:
                doseNominalBL = self.beamlets_gpu

            if worstCase != -1:
                doseScenario = cp.sparse.csc_matrix.dot(self.scenariosBL[worstCase], weights)
                doseScenarioBL = cp.sparse.csc_matrix.dot(self.scenariosBL[worstCase], xDiag)
            dfTot = np.zeros((1, len(x)), dtype=np.float32)
        elif use_MKL == 1:
            doseNominal = sparse_dot_mkl.dot_product_mkl(self.beamlets, weights)
            if self.xSquare:
                doseNominalBL = sparse_dot_mkl.dot_product_mkl(self.beamlets, xDiag)
            else:
                doseNominalBL = self.beamlets

            if worstCase != -1:
                doseScenario = sparse_dot_mkl.dot_product_mkl(self.scenariosBL[worstCase], weights)
                doseScenarioBL = sparse_dot_mkl.dot_product_mkl(self.scenariosBL[worstCase], xDiag)
            dfTot = np.zeros((1, len(x)), dtype=np.float32)
        else:
            doseNominal = sp.csc_matrix.dot(self.beamlets, weights)
            if self.xSquare:
                doseNominalBL = sp.csc_matrix.dot(self.beamlets, xDiag)
            else:
                doseNominalBL = self.beamlets
            doseNominalBL = sp.csc_matrix.transpose(doseNominalBL)
            if worstCase != -1:
                doseScenario = sp.csc_matrix.dot(self.scenariosBL[worstCase], weights)
                doseScenarioBL = sp.csc_matrix.dot(self.scenariosBL[worstCase], xDiag)
                doseScenarioBL = sp.csc_matrix.transpose(doseScenarioBL)
            dfTot = np.zeros((len(x), 1), dtype=np.float32)

        for objective in self.list:
            if worstCase != -1 and objective.robust:
                doseTotal = doseScenario
                doseBL = doseScenarioBL
            else:
                doseTotal = doseNominal
                doseBL = doseNominalBL

            if objective.metric == objective.Metrics.DMAX:
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.limitValue)
                    f = cp.maximum(0, doseTotal[maskVec_gpu] - limitValue_gpu.astype(cp.float32))
                else:
                    f = np.maximum(0, doseTotal[objective.maskVec] - objective.limitValue)

                if self.GPU_acceleration:
                    f = cpx.scipy.sparse.diags(f, format='csc')
                    df = cp.sparse.csc_matrix.dot(f, doseBL[maskVec_gpu, :])
                    dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                elif use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)

            elif objective.metric == objective.Metrics.DMEAN:
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.limitValue)
                    f = cp.maximum(0, cp.mean(doseTotal[maskVec_gpu], dtype=cp.float32) - limitValue_gpu.astype(
                        cp.float32))
                else:
                    f = np.maximum(0, np.mean(doseTotal[objective.maskVec],
                                              dtype=np.float32) - objective.limitValue)

                if self.GPU_acceleration:
                    try:
                        df = cpx.scipy.sparse.csr_matrix.multiply(doseBL[maskVec_gpu, :], float(
                            f))  # inconsistent behaviour when multiplied by scalar ?cupy/_compressed
                        dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                    except ValueError:
                        df = cpx.scipy.sparse.csr_matrix.multiply(doseBL[maskVec_gpu, :].T, float(
                            f))  # inconsistent behaviour when multiplied by scalar ?cupy/_compressed
                        dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=1)).get().T
                elif use_MKL == 1:
                    df = sp.csr_matrix.multiply(doseBL[objective.maskVec, :], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)

            elif objective.metric == objective.Metrics.DMIN:
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.limitValue)
                    f = cp.minimum(0, doseTotal[maskVec_gpu] - limitValue_gpu.astype(cp.float32))

                else:
                    f = np.minimum(0, doseTotal[objective.maskVec] - objective.limitValue)

                if self.GPU_acceleration:
                    f = cpx.scipy.sparse.diags(f, format='csc')
                    df = cp.sparse.csc_matrix.dot(f, doseBL[maskVec_gpu, :])
                    dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                elif use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)

            elif objective.metric == objective.Metrics.DUNIFORM:
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.limitValue)
                    f = doseTotal[maskVec_gpu] - limitValue_gpu.astype(cp.float32)

                else:
                    f = doseTotal[objective.maskVec] - objective.limitValue

                if self.GPU_acceleration:
                    f = cpx.scipy.sparse.diags(f, format='csc')
                    df = cp.sparse.csc_matrix.dot(f, doseBL[maskVec_gpu, :])
                    dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                elif use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)

            elif objective.metric == objective.Metrics.DFALLOFF:
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.voxelwiseLimitValue).astype(cp.float32)
                    f = cp.maximum(0, doseTotal[maskVec_gpu] - limitValue_gpu)

                else:
                    f = np.maximum(0, doseTotal[objective.maskVec] - objective.voxelwiseLimitValue)

                if self.GPU_acceleration:
                    f = cpx.scipy.sparse.diags(f, format='csc')
                    df = cp.sparse.csc_matrix.dot(f, doseBL[maskVec_gpu, :])
                    dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                elif use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)

            elif objective.metric == objective.Metrics.DVHMIN:
                d_ref = self._calcInverseDVH(objective.volume, doseTotal[objective.maskVec])
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.limitValue)
                    f = cp.minimum(0, doseTotal[maskVec_gpu] - limitValue_gpu.astype(cp.float32))
                    f[doseTotal[maskVec_gpu] < d_ref] = 0
                else:
                    f = np.minimum(0, doseTotal[objective.maskVec] - objective.limitValue)
                    f[doseTotal[objective.maskVec] < d_ref] = 0


                if self.GPU_acceleration:
                    f = cpx.scipy.sparse.diags(f, format='csc')
                    df = cp.sparse.csc_matrix.dot(f, doseBL[maskVec_gpu, :])
                    dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                elif use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)

            elif objective.metric == objective.Metrics.DVHMAX:
                d_ref = self._calcInverseDVH(objective.volume, doseTotal[objective.maskVec])
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.limitValue)
                    f = cp.maximum(0, doseTotal[maskVec_gpu] - limitValue_gpu.astype(cp.float32))
                    f[doseTotal[maskVec_gpu] > d_ref] = 0
                else:
                    f = np.maximum(0, doseTotal[objective.maskVec] - objective.limitValue)
                    f[doseTotal[objective.maskVec] > d_ref] = 0
                if self.GPU_acceleration:
                    f = cpx.scipy.sparse.diags(f, format='csc')
                    df = cp.sparse.csc_matrix.dot(f, doseBL[maskVec_gpu, :])
                    dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                elif use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)
            elif objective.metric == objective.Metrics.EUDMAX:
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.limitValue)
                    EUDa_gpu = cp.asarray(objective.EUDa)
                    power_dose = doseTotal[maskVec_gpu] ** EUDa_gpu
                    EUD_a = cp.mean(power_dose) ** (1/EUDa_gpu)
                    f = (1 / len(maskVec_gpu)) ** ((1 - EUDa_gpu)/ EUDa_gpu) * cp.sum(power_dose) ** ((1 - EUDa_gpu) / EUDa_gpu) * doseTotal[maskVec_gpu] ** (EUDa_gpu - 1) * cp.maximum(0, EUD_a - limitValue_gpu)
                else:
                    power_dose = doseTotal[objective.maskVec] ** objective.EUDa
                    EUD_a = np.mean(power_dose) ** (1/objective.EUDa)
                    f = (1 / len(objective.maskVec)) ** ((1 - objective.EUDa)/ objective.EUDa) * np.sum(power_dose) ** ((1 - objective.EUDa) / objective.EUDa) * doseTotal[objective.maskVec] ** (objective.EUDa - 1) * max(0, EUD_a - objective.limitValue)

                if self.GPU_acceleration:
                    f = cpx.scipy.sparse.diags(f, format='csc')
                    df = cp.sparse.csc_matrix.dot(f, doseBL[maskVec_gpu, :])
                    dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                elif use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)
            elif objective.metric == objective.Metrics.EUDMIN:
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.limitValue)
                    EUDa_gpu = cp.asarray(objective.EUDa)
                    power_dose = doseTotal[maskVec_gpu] ** EUDa_gpu
                    EUD_a = cp.mean(power_dose) ** (1/EUDa_gpu)
                    f = (1 / len(maskVec_gpu)) ** ((1 - EUDa_gpu)/ EUDa_gpu) * cp.sum(power_dose) ** ((1 - EUDa_gpu) / EUDa_gpu) * doseTotal[maskVec_gpu] ** (EUDa_gpu - 1) * cp.minimum(0, EUD_a - limitValue_gpu)
                else:
                    power_dose = doseTotal[objective.maskVec] ** objective.EUDa
                    EUD_a = np.mean(power_dose) ** (1/objective.EUDa)
                    f = (1 / len(objective.maskVec)) ** ((1 - objective.EUDa)/ objective.EUDa) * np.sum(power_dose) ** ((1 - objective.EUDa) / objective.EUDa) * doseTotal[objective.maskVec] ** (objective.EUDa - 1) * min(0,EUD_a - objective.limitValue)

                if self.GPU_acceleration:
                    f = cpx.scipy.sparse.diags(f, format='csc')
                    df = cp.sparse.csc_matrix.dot(f, doseBL[maskVec_gpu, :])
                    dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                elif use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)
            elif objective.metric == objective.Metrics.EUDUNIFORM:
                if self.GPU_acceleration:
                    maskVec_gpu = cp.asarray(objective.maskVec)
                    limitValue_gpu = cp.asarray(objective.limitValue)
                    EUDa_gpu = cp.asarray(objective.EUDa)
                    power_dose = doseTotal[maskVec_gpu] ** EUDa_gpu
                    EUD_a = cp.mean(power_dose) ** (1/EUDa_gpu)
                    f = (1 / len(maskVec_gpu)) ** ((1 - EUDa_gpu)/ EUDa_gpu) * cp.sum(power_dose) ** ((1 - EUDa_gpu) / EUDa_gpu) * doseTotal[maskVec_gpu] ** (EUDa_gpu - 1) * (EUD_a - limitValue_gpu)
                else:
                    power_dose = doseTotal[objective.maskVec] ** objective.EUDa
                    EUD_a = np.mean(power_dose) ** (1/objective.EUDa)
                    f = (1 / len(objective.maskVec)) ** ((1 - objective.EUDa)/ objective.EUDa) * np.sum(power_dose) ** ((1 - objective.EUDa) / objective.EUDa) * doseTotal[objective.maskVec] ** (objective.EUDa - 1) * (EUD_a - objective.limitValue)

                if self.GPU_acceleration:
                    f = cpx.scipy.sparse.diags(f, format='csc')
                    df = cp.sparse.csc_matrix.dot(f, doseBL[maskVec_gpu, :])
                    dfTot += objective.weight * (cpx.scipy.sparse.csr_matrix.mean(df, axis=0)).get()
                elif use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)
                    
            else:
                raise Exception(objective.metric + ' is not supported as an objective metric')

        if self.xSquare:
            dfTot = 4 * dfTot
        else:
            dfTot = 2 * dfTot
        dfTot = np.squeeze(np.asarray(dfTot)).astype(np.float64)

        if self.GPU_acceleration:
            del maskVec_gpu, limitValue_gpu, f, df, doseNominal, weights, xDiag
            cp._default_memory_pool.free_all_blocks()

        return dfTot
    
    def _calcInverseDVH(self, volume, dose):
        if self.GPU_acceleration:
            sorted_dose = cp.sort(dose.flatten())
            volume_cupy = cp.asarray(volume)
            index = cp.rint((1 - volume_cupy) * len(sorted_dose)).astype(np.int32)
        else:
            sorted_dose = np.sort(dose.flatten())
            index = int((1 - volume) * len(sorted_dose))
        return sorted_dose[index]

    def _eval(self, x):
        f = self.computeFidelityFunction(x)
        return f

    def _grad(self, x):
        g = self.computeFidelityGradient(x)
        return g
