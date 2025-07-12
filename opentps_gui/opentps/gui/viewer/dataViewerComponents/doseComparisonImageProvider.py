import typing
from enum import Enum

import numpy as np

from opentps.core.data.images import DoseImage
from opentps.core.data.images._image3D import Image3D
from opentps.core.processing.imageProcessing import resampler3D
from opentps.core import Event


class DoseComparisonImageProvider:
    class Metric(Enum):
        ABSOLUTE_DIFFERENCE = "absolute difference"
        DIFFERENCE = "difference"
        GAMMA = "gamma"
        DEFAULT = "difference"

    def __init__(self):
        self.doseComparisonImageChangedSignal = Event(object)

        self._dose1:typing.Optional[DoseImage] = None
        self._dose2:typing.Optional[DoseImage] = None
        self._comparisonMetric = self.Metric.DEFAULT
        self._doseComparisonImage = None

    @property
    def doseComparisonImage(self) -> typing.Optional[Image3D]:
        return self._doseComparisonImage

    @property
    def dose1(self):
        return self._dose1

    @dose1.setter
    def dose1(self, dose:DoseImage):
        self._disconnectAll()
        self._dose1 = dose
        self._updateDoseComparison()
        self._connectAll()

    @property
    def dose2(self):
        return self._dose2

    @dose2.setter
    def dose2(self, dose:DoseImage):
        self._disconnectAll()
        self._dose2 = dose
        self._updateDoseComparison()
        self._connectAll()

    @property
    def comparisonMetric(self):
        return self._comparisonMetric

    @comparisonMetric.setter
    def comparisonMetric(self, m):
        self._comparisonMetric = m
        self._updateDoseComparison()

    def _updateDoseComparison(self):
        if self._dose1 is None:
            dose = None
        elif self._dose2 is None:
            dose = None
        else:
            dose = DoseImage.fromImage3D(self._dose1, patient=None)
            dose2 = resampler3D.resampleImage3DOnImage3D(self._dose2, dose, inPlace=False)
            dose2.patient = None

            if self._comparisonMetric == self.Metric.DIFFERENCE:
                dose.imageArray = dose.imageArray - dose2.imageArray
            elif self._comparisonMetric == self.Metric.ABSOLUTE_DIFFERENCE:
                dose.imageArray = np.abs(dose.imageArray - dose2.imageArray)
            elif self.comparisonMetric == self.Metric.GAMMA:
                raise NotImplementedError

        self._doseComparisonImage = dose
        if not (self._doseComparisonImage is None):
            self._setName()
        self.doseComparisonImageChangedSignal.emit(self._doseComparisonImage)

    def _disconnectAll(self):
        if not (self._dose1 is None):
            self._dose1.nameChangedSignal.disconnect(self._setName)
        if not (self._dose2 is None):
            self._dose2.nameChangedSignal.disconnect(self._setName)

    def _connectAll(self):
        if not (self._dose1 is None):
            self._dose1.nameChangedSignal.connect(self._setName)
        if not (self._dose2 is None):
            self._dose2.nameChangedSignal.connect(self._setName)

    def _setName(self, *args):
        name = ''

        if self._comparisonMetric==self.Metric.DIFFERENCE:
            name = 'Diff. btw. '
        elif self._comparisonMetric==self.Metric.ABSOLUTE_DIFFERENCE:
            name = 'Abs. diff. btw. '
        elif self._comparisonMetric==self.Metric.GAMMA:
            name = 'Gamma ind. btw. '

        name += self._dose1.name
        name += ' and '
        name += self._dose2.name

        self._doseComparisonImage.name = name
