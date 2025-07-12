from typing import Union, Optional, Sequence

__all__ = ['DVHBand']

import numpy as np

from opentps.core import Event


class DVHBand():
    """
    Class representing a DVH band for a given ROI. The DVH band is defined by a nominal DVH and a lower and upper
    envelope of DVH scenarios.
    Lower and upper envelope of DVH scenarios are computed from a set of dose distributions.

    Attributes
    ----------
    roiName : str
        name of the ROI
    dose : np.array
        1D numpy array representing the discretization of the dose [0, maxDose]
    nominalDVH : DVH
        nominal DVH
    volumeLow : np.array
        lower envelope of DVH scenarios in % of volume
    volumeHigh : np.array
        upper envelope of DVH scenarios in % of volume
    volumeAbsoluteLow : np.array
        lower envelope of DVH scenarios in cm^3
    volumeAbsoluteHigh : np.array
        upper envelope of DVH scenarios in cm^3
    Dmean : list
        mean doses in Gy
    D98 : list
        98% doses in Gy
    D95 : list
        95% doses in Gy
    D50 : list
        50% doses in Gy
    D5 : list
        5% doses in Gy
    D2 : list
        2% doses in Gy
    Dmin : list
        minimum doses in Gy
    Dmax : list
        maximum doses in Gy
    """
    def __init__(self, roiName: str = None, dose: np.array = None):

        self.dataUpdatedEvent = Event()

        self._roiName = roiName

        self._nominalDVH = None
        self._dose = dose # 1D numpy array representing the discretization of the dose [0, maxDose]
        self._volumeLow = None # lower envelope of DVH scenarios in % of volume
        self._volumeHigh = None # upper envelope of DVH scenarios in % of volume
        self._volumeAbsoluteLow = None # in cm^3
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
        """
        Compute DVH metrics from the DVH band
        """
        # compute metrics
        self._D98 = self.computeBandDx(98)
        self._D95 = self.computeBandDx(95)
        self._D50 = self.computeBandDx(50)
        self._D5 = self.computeBandDx(5)
        self._D2 = self.computeBandDx(2)

    def computeBandDx(self, x):
        """
        Compute the Dx metric from the DVH band

        Parameters
        ----------
        x : float
            x value in % of volume
        Returns
        -------
        [low_Dx,high_Dx] : list
            Dx metric in Gy
        """
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
