from abc import abstractmethod
from typing import Optional

from Core.Data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images._ctImage import CTImage
from Core.Data.Images._doseImage import DoseImage
from Core.Data.Images._roiMask import ROIMask
from Core.Data.Plan._rtPlan import RTPlan
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
    def computeBeamlets(self, ct: CTImage, plan: RTPlan, roi: Optional[ROIMask] = None):
        raise NotImplementedError()

class DoseInfluenceCalculatorException(Exception):
    pass