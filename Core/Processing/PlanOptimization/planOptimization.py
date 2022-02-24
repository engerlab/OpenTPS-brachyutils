import logging

import numpy as np
import scipy.sparse as sp

try:
    import sparse_dot_mkl

    use_MKL = 1
except:
    use_MKL = 0

from Core.Processing.PlanOptimization.Solvers import gradientDescent, bfgs, fista, localSearch, mip, sparcling

logger = logging.getLogger(__name__)


class Optimizer:
    def __init__(self, modality='IMPT', method='Scipy-LBFGS', beamletBased=False):
        self.modality = modality
        self.method = method
        self.beamletBased = beamletBased
        # self.solver =

        if self.modality == 'IMPT':
            if self.beamletBased:
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
                    pass
                else:
                    logger.error(
                        'Method {} is not implemented. Pick among ["Scipy-lBFGS", "Gradient", "BFGS", "FISTA"]'.format(
                            self.method))
            else:
                self.method = 'Beamlet-free'

        elif self.modality == 'ArcPT':
            if self.method == 'FISTA':
                self.solver = fista.FISTA()
            elif self.method == 'LS':
                self.solver = localSearch.LS()
            elif self.method == 'MIP':
                self.solver = mip.MIP()
            elif self.method == 'SPArcling':
                self.solver = sparcling.SPArCling()
            else:
                logger.error(
                    'Method {} is not implemented. Pick among ["FISTA","LS","MIP","SPArcling"]'.format(self.method))
        else:
            logger.error('Modality {} does not exist. Pick among ["IMPT","ArcPT"].'.format(self.modality))

    def optimize(self, plan, ct, contours, functions, **kwargs):
        opti_params = kwargs
        # initialize objective function and ROI masks
        logger.info("Initialize objective function ...")
        plan.Objectives.initialize_objective_function(contours)

        ROI_objectives = np.zeros(plan.beamlets.NbrVoxels).astype(bool)
        ROI_robust_objectives = np.zeros(plan.beamlets.NbrVoxels).astype(bool)

        robust = False
        for objective in plan.Objectives.list:
            if objective.Robust:
                robust = True
                ROI_robust_objectives = np.logical_or(ROI_robust_objectives, objective.Mask_vec)
            else:
                ROI_objectives = np.logical_or(ROI_objectives, objective.Mask_vec)
        ROI_objectives = np.logical_or(ROI_objectives, ROI_robust_objectives)

        # reload beamlets and crop to optimization ROI
        logger.info("Load beamlets ...")
        plan.beamlets.load()
        if use_MKL == 1:
            plan.beamlets.BeamletMatrix = sparse_dot_mkl.dot_product_mkl(
                sp.diags(ROI_objectives.astype(np.float32), format='csc'), plan.beamlets.BeamletMatrix)
        else:
            plan.beamlets.BeamletMatrix = sp.csc_matrix.dot(
                sp.diags(ROI_objectives.astype(np.float32), format='csc'),
                plan.beamlets.BeamletMatrix)

        if robust:
            for s in range(len(plan.scenarios)):
                plan.scenarios[s].load()
                if use_MKL == 1:
                    plan.scenarios[s].BeamletMatrix = sparse_dot_mkl.dot_product_mkl(
                        sp.diags(ROI_robust_objectives.astype(np.float32), format='csc'),
                        plan.scenarios[s].BeamletMatrix)
                else:
                    plan.scenarios[s].BeamletMatrix = sp.csc_matrix.dot(
                        sp.diags(ROI_robust_objectives.astype(np.float32), format='csc'),
                        plan.scenarios[s].BeamletMatrix)

        # Total Dose calculation
        Weights = np.ones(plan.beamlets.NbrSpots, dtype=np.float32)
        if use_MKL == 1:
            TotalDose = sparse_dot_mkl.dot_product_mkl(plan.beamlets.BeamletMatrix, Weights)
        else:
            TotalDose = sp.csc_matrix.dot(plan.beamlets.BeamletMatrix, Weights)

        maxDose = np.max(TotalDose)
        try:
            x0 = opti_params['init_weights']
        except KeyError:
            x0 = (plan.Objectives.TargetPrescription / maxDose) * np.ones(plan.beamlets.NbrSpots, dtype=np.float32)

        # Optimization
        result = self.solver.solve(functions, x0, opti_params)

        weights = result['sol']
        crit = result['crit']
        niter = result['niter']
        time = result['time']
        cost = result['objective']
        logger.info(
            ' {} terminated in {} Iter, x = {}, f(x) = {}, time elapsed {}, time per iter {}' \
                .format(self.solver.__class__.__name__, niter, weights, cost, time, time / niter))

        # unload scenario beamlets
        for s in range(len(plan.scenarios)):
            plan.scenarios[s].unload()

        # total dose
        logger.info("Total dose calculation ...")
        plan.update_spot_weights(weights)
        totalDose = plan.beamlets.Compute_dose_from_beamlets(weights)

        return weights, totalDose, cost
