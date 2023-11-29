import logging

from opentps.core.utils.applicationConfig import AbstractApplicationConfig


logger = logging.getLogger(__name__)


class PlanOptimizationConfig(AbstractApplicationConfig):
    """
    This class is used to store the configuration of the plan optimization. Inherit from AbstractApplicationConfig.

    Attribute
    ----------
    imptSolver : str
        The solver used for the IMPT optimization. Default is 'Scipy-LBFGS'.
    imptMaxIter : int
        The maximum number of iterations for the IMPT optimization. Default is 100.
    """
    def __init__(self):
        super().__init__()

        self._writeAllFieldsIfNotAlready()

    def _writeAllFieldsIfNotAlready(self):
        self.imptSolver
        self.imptMaxIter

    @property
    def imptSolver(self) -> str:
        return self.getConfigField("solvers", "IMPT", 'Scipy-LBFGS')

    @imptSolver.setter
    def imptSolver(self, solver:str):
        self.setConfigField("solvers", "IMPT", solver)

    @property
    def imptMaxIter(self) -> int:
        return int(self.getConfigField("IMPT", "maxIter", int(100)))

    @imptMaxIter.setter
    def imptMaxIter(self, maxIter:int):
        self.setConfigField("IMPT", "maxIter", maxIter)
