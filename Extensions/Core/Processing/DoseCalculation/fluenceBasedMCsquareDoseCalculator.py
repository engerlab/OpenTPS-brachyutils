from typing import Optional

from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.rtPlan import RTPlan
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator


class FluenceBasedMCsquareDoseCalculator(MCsquareDoseCalculator):
    def __init__(self):
        super().__init__()

        self._distToIsocenter = 0.0

    @property
    def distanceToIsocenter(self) -> float:
        return self._distToIsocenter

    @distanceToIsocenter.setter
    def distanceToIsocenter(self, dist: float):
        self._distToIsocenter = dist

    def computeDose(self, ct:CTImage, plan: RTPlan) -> DoseImage:
        return super().computeDose(ct, self._fluencePlan)

    def computeBeamlets(self, ct:CTImage, plan: RTPlan, roi:Optional[ROIMask]=None):
        return super().computeDose(ct, self._fluencePlan)

    @property
    def _fluencePlan(self) -> RTPlan:
        raise NotImplementedError()

    def _fluenceAtDist(self):
        raise NotImplementedError()