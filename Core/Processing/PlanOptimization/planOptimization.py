import logging
from Core.Processing.PlanOptimization.Solvers import gradientDescent

logger = logging.getLogger(__name__)


class Optimizer:
    def __init__(self, plan, ct, contours, modality='IMPT', method='Scipy-lBFGS', beamletBased=False, **kwargs):
        self.plan = plan
        self.ct = ct
        self.contours = contours
        self.modality = modality
        self.method = method
        self.beamletBased = beamletBased
        self.optiParams = kwargs

        if self.modality == 'IMPT':
            if self.beamletBased:
                if self.method == 'Scipy-lBFGS':
                    solver = solvers.scipyLBFGS
                elif self.method == 'Scipy-BFGS':
                    solver = solvers.scipyLBFGS
                elif self.method == 'Gradient':
                    solver = gradientDescent.GradientDescent()
                elif self.method == 'BFGS':
                    solver = solvers.bfgs
                elif self.method == "lBFGS":
                    solver = solvers.lbfgs
                elif self.method == "FISTA":
                    solver = solvers.fista
                    pass
                else:
                    logger.error(
                        'Method {} is not implemented. Pick among ["Scipy-lBFGS", "Gradient", "BFGS", "FISTA"]'.format(self.method))
            else:
                self.method == 'Beamlet-free'

        elif self.modality == 'ArcPT':
            if self.method == 'FISTA':
                solver = solvers.fista
            elif self.method == 'LS':
                solver = solvers.localSearch
            elif self.method == 'MIP':
                solver = solvers.mip
            elif self.method == 'SPArcling':
                solver = solvers.sparcling
            else:
                logger.error(
                    'Method {} is not implemented. Pick among ["FISTA","LS","MIP","SPArcling"]'.format(self.method))
        else:
            logger.error('Modality {} does not exist. Pick among ["IMPT","ArcPT"].'.format(self.modality))


    def solve(self):
        res =
        return res
