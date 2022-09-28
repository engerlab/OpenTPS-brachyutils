import logging

from opentps.core.utils.applicationConfig import AbstractApplicationConfig


logger = logging.getLogger(__name__)


class PlanOptimizationConfig(AbstractApplicationConfig):
    def __init__(self):
        super().__init__()

        self._writeAllFieldsIfNotAlready()

    def _writeAllFieldsIfNotAlready(self):
        self.beamletPrimaries
        self.finalDosePrimaries
        self.imptSolver
        self.imptMaxIter

    @property
    def beamletPrimaries(self) -> int:
        return int(self.getConfigField("MCsquare", "beamletPrimaries", int(1e4)))

    @beamletPrimaries.setter
    def beamletPrimaries(self, primaries:int):
        self.setConfigField("MCsquare", "beamletPrimaries", int(primaries))

    @property
    def finalDosePrimaries(self) -> int:
        return int(self.getConfigField("MCsquare", "finalDosePrimaries", int(1e8)))

    @finalDosePrimaries.setter
    def finalDosePrimaries(self, primaries: int):
        self.setConfigField("MCsquare", "finalDosePrimaries", int(primaries))

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
