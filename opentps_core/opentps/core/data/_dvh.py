
__all__ = ['DVH']

from typing import Union, Optional

import numpy as np

from opentps.core.data.images._doseImage import DoseImage
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data._roiContour import ROIContour
from opentps.core.processing.imageProcessing import resampler3D
from opentps.core import Event


class DVH:
    def __init__(self, roiMask:Union[ROIContour, ROIMask], dose:DoseImage=None, prescription=None):

        self.dataUpdatedEvent = Event()

        self._roiMask = roiMask
        self._roiName = roiMask.name
        self._doseImage = dose

        self._dose = None
        self._volume = None
        self._volume_absolute = None
        self._Dmean = 0
        self._D98 = 0
        self._D95 = 0
        self._D50 = 0
        self._D5 = 0
        self._D2 = 0
        self._Dmin = 0
        self._Dmax = 0
        self._Dstd = 0
        self._prescription = prescription

        if isinstance(roiMask, ROIMask):
            self._roiMask.dataChangedSignal.connect(self.computeDVH)

        if not (self._doseImage is None):
            self._doseImage.dataChangedSignal.connect(self.computeDVH)
            self.computeDVH()

    @property
    def dose(self):
        return self._doseImage

    @dose.setter
    def dose(self, dose:DoseImage):
        if dose==self._doseImage:
            return

        if not (self._doseImage is None):
            self._doseImage.dataChangedSignal.disconnect(self.computeDVH)

        self._doseImage = dose

        self._doseImage.dataChangedSignal.connect(self.computeDVH)
        self.computeDVH()

    @property
    def histogram(self):
        return self._dose, self._volume

    @property
    def name(self) -> Optional[str]:
        return self._roiName

    @property
    def Dmean(self) -> float:
        return self._Dmean

    @property
    def D98(self) -> float:
        return self._D98

    @property
    def D95(self) -> float:
        return self._D95

    @property
    def D50(self) -> float:
        return self._D50

    @property
    def D5(self) -> float:
        return self._D5

    @property
    def D2(self) -> float:
        return self._D2

    @property
    def Dmin(self):
        return self._Dmin

    @property
    def Dmax(self) -> float:
        return self._Dmax

    @property
    def Dstd(self) -> float:
        return self._Dstd

    def _convertContourToROI(self):
        if isinstance(self._roiMask, ROIContour):
            self._roiMask = self._roiMask.getBinaryMask(self._doseImage.origin, self._doseImage.gridSize, self._doseImage.spacing)
            self._roiMask.dataChangedSignal.connect(self.computeDVH)

    def computeDVH(self, maxDVH:float=100.0):
        if (self._doseImage is None):
            return

        self._convertContourToROI()

        if not(self._doseImage.hasSameGrid(self._roiMask)):
            self._doseImage = resampler3D.resampleImage3DOnImage3D(self._doseImage, self._roiMask, inPlace=False, fillValue=0.)

        dose = self._doseImage.imageArray
        mask = self._roiMask.imageArray.astype(bool)
        spacing = self._doseImage.spacing
        number_of_bins = 4096
        DVH_interval = [0, maxDVH]
        bin_size = (DVH_interval[1] - DVH_interval[0]) / number_of_bins
        bin_edges = np.arange(DVH_interval[0], DVH_interval[1] + 0.5 * bin_size, bin_size)
        bin_edges[-1] = maxDVH + dose.max()
        self._dose = bin_edges[:number_of_bins] + 0.5 * bin_size

        d = dose[mask]
        h, _ = np.histogram(d, bin_edges)
        h = np.flip(h, 0)
        h = np.cumsum(h)
        h = np.flip(h, 0)
        self._volume = h * 100 / len(d)  # volume in %
        self._volume_absolute = h * spacing[0] * spacing[1] * spacing[2] / 1000  # volume in cm3

        # compute metrics
        self._Dmean = np.mean(d)
        self._Dstd = np.std(d)
        self._Dmin = d.min() if len(d) > 0 else 0
        self._Dmax = d.max() if len(d) > 0 else 0
        self._D98 = self.computeDx(98)
        self._D95 = self.computeDx(95)
        self._D50 = self.computeDx(50)
        self._D5 = self.computeDx(5)
        self._D2 = self.computeDx(2)

        self.dataUpdatedEvent.emit()

    def computeDx(self, percentile:float, return_percentage:bool=False) -> float:
        """
        Compute Dx metric (e.g. D95% if x=95, dose that is reveived in at least 95% of the volume)

        Parameters
        ----------
        percentile: float
          Percentage of volume

        return_percentage: bool
          Whether to return the dose in Gy on % of the prescription

        Return
        ------
        Dx: float
          Dose received in at least x % of the volume contour

        """
        index = np.searchsorted(-self._volume, -percentile)
        if (index > len(self._volume) - 2): index = len(self._volume) - 2
        volume = self._volume[index]
        volume2 = self._volume[index + 1]
        if (volume == volume2):
            Dx = self._dose[index]
        else:
            w2 = (volume - percentile) / (volume - volume2)
            w1 = (percentile - volume2) / (volume - volume2)
            Dx = w1 * self._dose[index] + w2 * self._dose[index + 1]
            if Dx < 0: Dx = 0

        if return_percentage:
            assert self._prescription is not None
            return (Dx / self._prescription) * 100
        return Dx

    def computeDcc(self, x:float, return_percentage:bool=False) -> float:
        """
        Compute Dcc metric (e.g. D200cc if x=200 for minimal dose that is received the most irradiated 200cm^3)

        Parameters
        ----------
        x: float
          Volume in cm^3

        return_percentage: bool
          Whether to return the dose in Gy on % of the prescription

        Return
        ------
        Dcc: float
          Dose received

        """
        index = np.searchsorted(-self._volume_absolute, -x)
        if (index > len(self._volume) - 2): index = len(self._volume) - 2
        volume = self._volume_absolute[index]
        volume2 = self._volume_absolute[index + 1]
        if (volume == volume2):
            Dcc = self._dose[index]
        else:
            w2 = (volume - x) / (volume - volume2)
            w1 = (x - volume2) / (volume - volume2)
            Dcc = w1 * self._dose[index] + w2 * self._dose[index + 1]
            if Dcc < 0: Dcc = 0

        if return_percentage:
            assert self._prescription is not None
            return (Dcc / self._prescription) * 100
        return Dcc

    def computeVg(self, x:float, return_percentage:bool=True) -> float:
        """
        Compute Vg metric (e.g. V5 if x=5: volume that received at least 5Gy)

        Parameters
        ----------
        x: float
          Dose in Gy

        return_percentage: bool
          Whether to return the volume in percentage or in cm^3

        Return
        ------
        out: float
          Volume that receives at least x Gy

        """

        # TODO: improve this code using interpolation instead of search
        index = np.searchsorted(self._dose, x)
        if return_percentage:
            return self._volume[index]
        else:
            return self._volume_absolute[index]

    def computeVx(self, x:float, return_percentage:bool=True) -> float:
        """
        Compute Vx metric (e.g. V95% if x=95: volume that received at least 95% of the prescription)

        Parameters
        ----------
        x: float
          Dose in % of prescription

        return_percentage: bool
          Whether to return the volume in percentage or in cm^3

        Return
        ------
        out: float
          Return volume that receives at least x % of the prescribed dose

        """
        assert self._prescription is not None
        dose_percentage = (self._dose / self._prescription) * 100
        # TODO: improve this code using interpolation instead of search
        index = np.searchsorted(dose_percentage, x)
        if return_percentage:
            return self._volume[index]
        else:
            return self._volume_absolute[index]



    def homogeneityIndex(self, method:float='Yan_2019') -> float:
        """
        Compute the homogeneity index of the contour

        Parameters
        ----------
        method: str
          Type of method for the computation.
          'conventional_1' and 'conventional_2' are conventional method based on the DVH metrics.
          'S-index' is the standard deviation of the dose. (see https://doi.org/10.1120/jacmp.v8i2.2390)
          'Yan_2019' comes from https://doi.org/10.1002/acm2.12739
          It is based on the area under an ideal dose-volume histogram curve (IA),
          the area under the achieved dose-volume histogram curve (AA), and the overlapping area between the IA and AA (OA).
          It is defined as the ratio of the square of OA to the product of the IA and AA.

        Return
        ------
        out: float
          Homogenity index

        """
        if method == 'conventional_1':
            assert self._prescription is not None
            return (self._D2 - self._D98) / self._prescription

        if method == 'conventional_2':
            return (self._D2 - self._D98) / self._D50

        if method == 'conventional_3':
            return self._D2 - self._D98

        if method == 'conventional_4':
            return self._D5 - self._D95

        if method == 'conventional_5':
            assert self._prescription is not None
            return self._Dmax / self._prescription

        if method == 'S-index':
            return self._Dstd

        if method == 'Yan_2019':
            assert self._prescription is not None
            index = np.searchsorted(self._dose, self._prescription)
            IA = self._dose[index - 1] * 100.  # area under ideal DVH (step function)
            AA = np.trapz(y=self._volume, x=self._dose)  # area under achieved DVH
            OA = np.trapz(y=self._volume[:index], x=self._dose[:index])  # overlapping area between IA and AA.
            assert OA <= IA  # cannot do better than the step function
            return OA ** 2 / (IA * AA)

        raise NotImplementedError(f'Homogenity index method {method} not implemented.')

    def conformityIndex(self, dose, Contour, body_contour, method="Paddick"):
        """
        Compute the conformity index describing how tightly the prescription dose is conforming to the target.

        Parameters
        ----------

        dose: RTdose
          The RTdose object

        Contour: ROIcontour
          ROIcontour object of the target

        body_contour: ROIcontour
          ROIcontour object of delineating the contour of the body of the patient

        method: str
          Method to use for computing the conformity index
          if method=='RTOG': use the Radiation therapy oncology group guidelines index (https://doi.org/10.1016/0360-3016(93)90548-A)
          if method=='Paddick': use Paddick index, improved RTOG by taking into account the location and shape of the prescription
          isodose with respect to the target volume (https://doi.org/10.3171/sup.2006.105.7.194)

        Return
        ------
        out: float
          Conformity index

        """
        assert self._prescription is not None
        percentile = 0.95  # ICRU reference isodose
        if method == 'RTOG':  # Radiation therapy oncology group guidelines (1993)
            # prescription isodose volume
            isodose_prescription_volume = np.sum(dose.Image[body_contour.Mask == 1] >= percentile * self._prescription)
            contour_volume = np.sum(Contour.Mask)
            return isodose_prescription_volume / contour_volume

        if method == 'Paddick':
            # prescription isodose volume
            isodose_prescription_volume = np.sum(dose.Image[body_contour.Mask == 1] >= percentile * self._prescription)
            # Target volume
            contour_volume = np.sum(Contour.Mask)
            # target volume covered by the prescription isodose volume
            contour_volume_covered_by_prescription = np.sum(
                dose.Image[Contour.Mask == 1] >= percentile * self._prescription)
            return contour_volume_covered_by_prescription ** 2 / (isodose_prescription_volume * contour_volume)

        raise NotImplementedError(f'Conformity index method {method} not implemented.')