
import logging
import os
import numpy as np

from opentps.core.utils.applicationConfig import AbstractApplicationConfig
from opentps.core.processing import planDeliverySimulation

logger = logging.getLogger(__name__)


class IrradiationDurationLUT(AbstractApplicationConfig):
    """
    Irradiation Duration look-up table (LUT).

    Attributes
    ----------
    LUTFile : str
        The LUT file.
    LUT : np.array
        The LUT.
    nominalEnergy : np.array
        The nominal energy.
    duration : np.array
        The duration.
    """
    def __init__(self):
        super().__init__()
        self._LUT = None
        self._writeAllFieldsIfNotAlready()

    def _writeAllFieldsIfNotAlready(self):
        self.LUT

    @property
    def _defaultLUTFile(self) -> str:
        return planDeliverySimulation.__path__[0] + os.sep + 'LUT_irradiation_durations.txt'

    @property
    def LUTFile(self) -> str:
        return self.getConfigField("IrradiationTimeLUT", "LUTFile", self._defaultLUTFile)

    @LUTFile.setter
    def LUTFile(self, path:str):
        if path==self.LUTFile:
            return

        self.setConfigField("IrradiationTimeLUT", "LUTFile", path)
        # self.LUTFileChangedSignal.emit(self.bdlFile)

    @property
    def LUT(self):
        if self._LUT is None:
            self._LUT = np.loadtxt(self.LUTFile, delimiter='\t', skiprows=1)
        return self._LUT

    @property
    def nominalEnergy(self):
        return self.LUT[:,0]

    @property
    def duration(self):
        return self.LUT[:,1]

    