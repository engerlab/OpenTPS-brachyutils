from abc import abstractmethod
from enum import Enum
from typing import Optional

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.rtPlan import RTPlan
from Core.event import Event


class AbstractDoseCalculator:
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
    def computeDose(self, ct:CTImage, pla: RTPlan) -> DoseImage:
        raise NotImplementedError()

class ProgressInfo:
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
