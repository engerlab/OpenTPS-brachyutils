import numpy as np
import scipy.sparse as sp

try:
    import sparse_dot_mkl

    use_MKL = 1
except:
    use_MKL = 0

from opentps.core.processing.planOptimization.objectives.baseFunction import BaseFunc


class DoseFidelity(BaseFunc):
    def __init__(self, plan, xSquare=True):
        super(DoseFidelity, self).__init__()
        self.list = plan.planDesign.objectives.fidObjList
        self.xSquare = xSquare
        self.beamlets = plan.planDesign.beamlets.toSparseMatrix()
        if plan.planDesign.scenarios:
            self.scenariosBL = [plan.planDesign.scenarios[s].toSparseMatrix() for s in
                                range(len(plan.planDesign.scenarios))]
        else:
            self.scenariosBL = []


    def computeFidelityFunction(self, x, returnWorstCase=False):
        if self.xSquare:
            weights = np.square(x).astype(np.float32)
        else:
            weights = x.astype(np.float32)

        fTot = 0.0
        fTotScenario = 0.0
        scenarioList = []

        # compute objectives for nominal scenario
        if use_MKL == 1:
            doseTotal = sparse_dot_mkl.dot_product_mkl(self.beamlets, weights)
        else:
            doseTotal = sp.csc_matrix.dot(self.beamlets, weights)
        for objective in self.list:
            if objective.metric == objective.Metrics.DMAX:
                f = np.mean(np.maximum(0, doseTotal[objective.maskVec] - objective.limitValue) ** 2)
            elif objective.metric == objective.Metrics.DMEAN:
                f = np.maximum(0, np.mean(doseTotal[objective.maskVec], dtype=np.float32) - objective.limitValue) ** 2
            elif objective.metric == objective.Metrics.DMIN:
                f = np.mean(np.minimum(0, doseTotal[objective.maskVec] - objective.limitValue) ** 2)
            else:
                raise Exception(objective.metric + ' is not supported as an objective metric')
            if not objective.robust:
                fTot += objective.weight * f
            else:
                fTotScenario += objective.weight * f

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
                else:
                    raise Exception(objective.metric + ' is not supported as an objective metric')

                fTotScenario += objective.weight * f

            scenarioList.append(fTotScenario)

        fTot += max(scenarioList)

        if not returnWorstCase:
            return fTot
        else:
            return fTot, scenarioList.index(
                max(scenarioList)) - 1  # returns id of the worst case scenario (-1 for nominal)

    def computeFidelityGradient(self, x):
        # get worst case scenario
        if self.scenariosBL:
            fTot, worstCase = self.computeFidelityFunction(x, returnWorstCase=True)
        else:
            worstCase = -1
        if self.xSquare:
            weights = np.square(x).astype(np.float32)
        else:
            weights = x.astype(np.float32)
        xDiag = sp.diags(x.astype(np.float32), format='csc')

        if use_MKL == 1:
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
                f = np.maximum(0, doseTotal[objective.maskVec] - objective.limitValue)
                if use_MKL == 1:
                    f = sp.diags(f.astype(np.float32), format='csc')
                    df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.maskVec, :])
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)

            elif objective.metric == objective.Metrics.DMEAN:
                f = np.maximum(0, np.mean(doseTotal[objective.maskVec], dtype=np.float32) - objective.limitValue)
                if use_MKL == 1:
                    df = sp.csr_matrix.multiply(doseBL[objective.maskVec, :], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=0)
                else:
                    df = sp.csr_matrix.multiply(doseBL[:, objective.maskVec], f)
                    dfTot += objective.weight * sp.csr_matrix.mean(df, axis=1)

            elif objective.metric == objective.Metrics.DMIN:
                f = np.minimum(0, doseTotal[objective.maskVec] - objective.limitValue)
                if use_MKL == 1:
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

        return dfTot

    def _eval(self, x):
        f = self.computeFidelityFunction(x)
        return f

    def _grad(self, x):
        g = self.computeFidelityGradient(x)
        return g
