
import logging
import os

import opentps.core.processing.doseCalculation.MCsquare.BDL as bdlModule
import opentps.core.processing.doseCalculation.MCsquare.Scanners as ScannerModule
from opentps.core import Event

from opentps.core.utils.applicationConfig import AbstractApplicationConfig

__all__ = ['DoseCalculationConfig']

logger = logging.getLogger(__name__)


class DoseCalculationConfig(AbstractApplicationConfig):
    """
    Configuration for dose calculation using Event

    """
    def __init__(self):
        super().__init__()

        self.beamletPrimariesChangedSignal = Event(int)
        self.finalDosePrimariesChangedSignal = Event(int)
        self.bdlFileChangedSignal = Event(str)
        self.scannerFolderChangedSignal = Event(str)

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
        if primaries==self.beamletPrimaries:
            return

        self.setConfigField("MCsquare", "beamletPrimaries", int(primaries))
        self.beamletPrimariesChangedSignal.emit(self.beamletPrimaries)

    @property
    def finalDosePrimaries(self) -> int:
        return int(self.getConfigField("MCsquare", "finalDosePrimaries", int(1e8)))

    @finalDosePrimaries.setter
    def finalDosePrimaries(self, primaries: int):
        if primaries==self.finalDosePrimaries:
            return

        self.setConfigField("MCsquare", "finalDosePrimaries", int(primaries))
        self.finalDosePrimariesChangedSignal.emit(self.finalDosePrimaries)

    @property
    def _defaultBDLFile(self) -> str:
        return bdlModule.__path__[0] + os.sep + 'BDL_default_DN_RangeShifter.txt'

    @property
    def bdlFile(self) -> str:
        return self.getConfigField("MCsquare", "bdlFile", self._defaultBDLFile)

    @bdlFile.setter
    def bdlFile(self, path:str):
        if path==self.bdlFile:
            return

        self.setConfigField("MCsquare", "bdlFile", path)
        self.bdlFileChangedSignal.emit(self.bdlFile)

    @property
    def _defaultScannerFolder(self) -> str:
        return ScannerModule.__path__[0] + os.sep  + 'UCL_Toshiba'

    @property
    def scannerFolder(self) -> str:
        return self.getConfigField("MCsquare", "scannerFolder", self._defaultScannerFolder)

    @scannerFolder.setter
    def scannerFolder(self, path:str):
        if path==self.scannerFolder:
            return

        self.setConfigField("MCsquare", "scannerFolder", path)
        self.scannerFolderChangedSignal.emit(self.scannerFolder)
