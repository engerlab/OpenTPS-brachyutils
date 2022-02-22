from typing import Optional

from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareCTCalibration import MCsquareCTCalibration
from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.MCsquare.bdl import BDL
from Core.Processing.DoseCalculation.abstractDoseCalculator import DoseCalculatorException
from Core.Processing.DoseCalculation.abstractDoseInfluenceCalculator import AbstractDoseInfluenceCalculator
from Core.Processing.DoseCalculation.abstractMCDoseCalculator import AbstractMCDoseCalculator


class MCSquareDoseCalculator(AbstractMCDoseCalculator, AbstractDoseInfluenceCalculator):
    def __init__(self):
        AbstractMCDoseCalculator.__init__(self)
        AbstractDoseInfluenceCalculator.__init__(self)

        self._ctCalibration = None
        self._mcsquareCTCalibration = None
        self._beamModel = None
        self._nbPrimaries = 0

    @property
    def ctCalibration(self) -> Optional[AbstractCTCalibration]:
        return self._ctCalibration

    @ctCalibration.setter
    def ctCalibration(self, ctCalibration: AbstractCTCalibration):
        self._ctCalibration = ctCalibration

    @property
    def beamModel(self) -> BDL:
        return self._beamModel

    @beamModel.setter
    def beamModel(self, beamModel: BDL):
        self._beamModel = beamModel

    @property
    def nbPrimaries(self) -> int:
        return self._nbPrimaries

    @nbPrimaries.setter
    def nbPrimaries(self, primaries: int):
        self._nbPrimaries = primaries

    def computeDose(self, ct:CTImage, plan, roi:Optional[ROIMask]=None) -> DoseImage:
        # TODO Should we have the possibility to set a ROI?
        raise NotImplementedError()

    def computeDoseInfluence(self, ct:CTImage, plan, roi:Optional[ROIMask]=None):
        raise NotImplementedError()

