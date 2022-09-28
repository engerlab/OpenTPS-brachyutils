from typing import Union, Optional, Sequence

__all__ = ['DVHBand']

import numpy as np

from opentps.core.data.images._doseImage import DoseImage
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data._roiContour import ROIContour
from opentps.core import Event


class DVHBand():
    def __init__(self, roiMask: Union[ROIContour, ROIMask], dose: DoseImage = None):

        self.dataUpdatedEvent = Event()

        self._roiName = roiMask.name

        self._nominalDVH = None
        self._dose = dose
        self._volumeLow = None
        self._volumeHigh = None
        self._volumeAbsoluteLow = None
        self._volumeAbsoluteHigh = None
        self._Dmean = [0, 0]
        self._D98 = [0, 0]
        self._D95 = [0, 0]
        self._D50 = [0, 0]
        self._D5 = [0, 0]
        self._D2 = [0, 0]
        self._Dmin = [0, 0]
        self._Dmax = [0, 0]

    @property
    def name(self) -> Optional[str]:
        return self._roiName

    @property
    def Dmean(self) -> Sequence[float]:
        return self._Dmean

    @property
    def D98(self) -> Sequence[float]:
        return self._D98

    @property
    def D95(self) -> Sequence[float]:
        return self._D95

    @property
    def D50(self) -> Sequence[float]:
        return self._D50

    @property
    def D5(self) -> Sequence[float]:
        return self._D5

    @property
    def D2(self) -> Sequence[float]:
        return self._D2

    @property
    def Dmin(self) -> Sequence[float]:
        return self._Dmin

    @property
    def Dmax(self) -> Sequence[float]:
        return self._Dmax

    def computeMetrics(self):
        # compute metrics
        self._D98 = self.computeBandDx(98)
        self._D95 = self.computeBandDx(95)
        self._D50 = self.computeBandDx(50)
        self._D5 = self.computeBandDx(5)
        self._D2 = self.computeBandDx(2)

    def computeBandDx(self, x):
        index = np.searchsorted(-self._volumeLow, -x)
        if index > len(self._volumeLow) - 2: index = len(self._volumeLow) - 2
        volume = self._volumeLow[index]
        volume2 = self._volumeLow[index + 1]
        if volume == volume2:
            low_Dx = self._dose[index]
        else:
            w2 = (volume - x) / (volume - volume2)
            w1 = (x - volume2) / (volume - volume2)
            low_Dx = w1 * self._dose[index] + w2 * self._dose[index + 1]
            if low_Dx < 0: low_Dx = 0

        index = np.searchsorted(-self._volumeHigh, -x)
        if index > len(self._volumeHigh) - 2: index = len(self._volumeHigh) - 2
        volume = self._volumeHigh[index]
        volume2 = self._volumeHigh[index + 1]
        if volume == volume2:
            high_Dx = self._dose[index]
        else:
            w2 = (volume - x) / (volume - volume2)
            w1 = (x - volume2) / (volume - volume2)
            high_Dx = w1 * self._dose[index] + w2 * self._dose[index + 1]
            if high_Dx < 0: high_Dx = 0

        return [low_Dx, high_Dx]
