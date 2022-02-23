from abc import abstractmethod
from typing import Optional

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Processing.DoseCalculation.abstractDoseCalculator import ProgressInfo
from Core.event import Event


class AbstractDoseInfluenceCalculator:
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
    # TODO: specify plan type when class RTPlan is defined
    def computeDoseInfluence(self, ct: CTImage, plan, roi: Optional[ROIMask] = None):
        raise NotImplementedError()

class DoseInfluenceCalculatorException(Exception):
    pass