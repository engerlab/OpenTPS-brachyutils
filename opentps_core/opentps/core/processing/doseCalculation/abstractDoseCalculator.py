from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from typing import Optional

from opentps.core import Event

__all__ = ['AbstractDoseCalculator']

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentps.core.data.images._doseImage import DoseImage
    from opentps.core.data.CTCalibrations import AbstractCTCalibration
    from opentps.core.data.images._ctImage import CTImage
    from opentps.core.data.plan._rtPlan import RTPlan

class AbstractDoseCalculator:
    """
    Abstract class for dose calculation
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
    def computeDose(self, ct:CTImage, plan: RTPlan) -> DoseImage:
        raise NotImplementedError()

class ProgressInfo:
    """
    Progress information for dose calculation
    /!\ Not implemented yet
    """
    class Status(Enum):
        RUNNING = 'RUNNING'
        IDLE = 'IDLE'
        DEFAULT = 'IDLE'

    def __init__(self):
        self.status = self.Status.DEFAULT
        self.progressPercentage = 0.0
        self.msg = ''

class DoseCalculatorException(Exception):
    pass
