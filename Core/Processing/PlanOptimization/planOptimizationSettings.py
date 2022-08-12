import logging

from Core.Utils.applicationConfig import AbstractApplicationConfig


logger = logging.getLogger(__name__)


class PlanOptimizationSettings(AbstractApplicationConfig):
    def __init__(self):
        super().__init__()

        a = self.beamletPrimaries
        a = self.finalDosePrimaries

    @property
    def beamletPrimaries(self) -> int:
        return int(self.getConfigField("MCsquare", "beamletPrimaries", int(1e6)))

    @beamletPrimaries.setter
    def beamletPrimaries(self, primaries:int):
        self.setConfigField("MCsquare", "beamletPrimaries", int(primaries))

    @property
    def finalDosePrimaries(self) -> int:
        return int(self.getConfigField("MCsquare", "finalDosePrimaries", int(1e8)))

    @finalDosePrimaries.setter
    def finalDosePrimaries(self, primaries: int):
        self.setConfigField("MCsquare", "finalDosePrimaries", int(primaries))
