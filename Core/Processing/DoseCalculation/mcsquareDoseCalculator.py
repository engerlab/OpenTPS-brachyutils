from typing import Optional

from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareCTCalibration import MCsquareCTCalibration
from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Processing.DoseCalculation.abstractDoseCalculator import DoseCalculatorException
from Core.Processing.DoseCalculation.abstractDoseInfluenceCalculator import AbstractDoseInfluenceCalculator
from Core.Processing.DoseCalculation.abstractMCDoseCalculator import AbstractMCDoseCalculator


class MCSquareDoseCalculator(AbstractMCDoseCalculator, AbstractDoseInfluenceCalculator):
    def __init__(self):
        AbstractMCDoseCalculator.__init__(self)
        AbstractDoseInfluenceCalculator.__init__(self)

        self._originalCTCalibration = None
        self._mcsquareCTCalibration = None
        self._beamModel = None
        self._nbPrimaries = 0

    @property
    def ctCalibration(self) -> Optional[AbstractCTCalibration]:
        return self._originalCTCalibration

    @ctCalibration.setter
    def ctCalibration(self, ctCalibration: AbstractCTCalibration):
        if not isinstance(ctCalibration, MCsquareCTCalibration):
            self._mcsquareCTCalibration = self.__class__._convertCTCalibrationToMCsquare(ctCalibration)
        else:
            self._mcsquareCTCalibration = ctCalibration

        self._originalCTCalibration = ctCalibration

    @staticmethod
    def _convertCTCalibrationToMCsquare(ctCalibration: AbstractCTCalibration) -> MCsquareCTCalibration:
        try:
            return MCsquareCTCalibration.fromCTCalibration(ctCalibration)
        except Exception as e:
            raise DoseCalculatorException('CT Calibration cannot be converted into an MCsquareCTCalibration') from e

    @property
    def beamModel(self):
        return self._beamModel

    @beamModel.setter
    def beamModel(self, beamModel):
        # TODO beam model is not yet implemented. Can there be different beam models like there can be different CT calibrations?
        raise NotImplementedError()

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

