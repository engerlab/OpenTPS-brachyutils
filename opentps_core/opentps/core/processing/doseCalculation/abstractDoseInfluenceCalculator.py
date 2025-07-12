from abc import abstractmethod
from typing import Optional

from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.processing.doseCalculation.abstractDoseCalculator import ProgressInfo
from opentps.core import Event

__all__ = ['AbstractDoseInfluenceCalculator']

class AbstractDoseInfluenceCalculator:
    """
    Abstract class for dose influence calculation
    """
    def __init__(self):
        self.progressEvent = Event(ProgressInfo)

    @property
    def ctCalibration(self) -> Optional[AbstractCTCalibration]:
        raise NotImplementedError()

    @ctCalibration.setter
    def ctCalibration(self, ctCalibration: AbstractCTCalibration):
        raise NotImplementedError()

    @property
    def beamModel(self):
        raise NotImplementedError()

    @beamModel.setter
    def beamModel(self, beamModel):
        raise NotImplementedError()

    @abstractmethod
    def computeBeamlets(self, ct: CTImage, plan: RTPlan, roi: Optional[ROIMask] = None):
        raise NotImplementedError()

class DoseInfluenceCalculatorException(Exception):
    pass