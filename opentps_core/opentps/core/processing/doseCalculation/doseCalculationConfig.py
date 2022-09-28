
import logging
import os

import opentps.core.processing.doseCalculation.MCsquare.BDL as bdlModule
import opentps.core.processing.doseCalculation.MCsquare.Scanners as ScannerModule

from opentps.core.utils.applicationConfig import AbstractApplicationConfig

__all__ = ['DoseCalculationConfig']

logger = logging.getLogger(__name__)


class DoseCalculationConfig(AbstractApplicationConfig):
    def __init__(self):
        super().__init__()

        self._writeAllFieldsIfNotAlready()

    def _writeAllFieldsIfNotAlready(self):
        self.beamletPrimaries
        self.finalDosePrimaries
        self.bdlFile
        self.scannerFolder

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
    def _defaultBDLFile(self) -> str:
        return bdlModule.__path__[0] + os.sep + 'BDL_default_DN_RangeShifter.txt'

    @property
    def bdlFile(self) -> str:
        return self.getConfigField("MCsquare", "bdlFile", self._defaultBDLFile)

    @bdlFile.setter
    def bdlFile(self, path:str):
        self.setConfigField("MCsquare", "bdlFile", path)

    @property
    def _defaultScannerFolder(self) -> str:
        return ScannerModule.__path__[0] + os.sep  + 'UCL_Toshiba'

    @property
    def scannerFolder(self) -> str:
        return self.getConfigField("MCsquare", "scannerFolder", self._defaultScannerFolder)

    @scannerFolder.setter
    def scannerFolder(self, path:str):
        self.setConfigField("MCsquare", "scannerFolder", path)
