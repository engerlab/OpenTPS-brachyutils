
__all__ = ['Image2D']


import copy
from typing import Sequence

import numpy as np

from opentps.core.data._patientData import PatientData
from opentps.core import Event


class Image2D(PatientData):
    def __init__(self, imageArray=None, name="2D Image", origin=(0, 0, 0), spacing=(1, 1), angles=(0, 0, 0), seriesInstanceUID=None, patient=None):
        self.dataChangedSignal = Event()

        self._imageArray = imageArray
        self._origin = np.array(origin)
        self._spacing = np.array(spacing)
        self._angles = np.array(angles)

        super().__init__(name=name, seriesInstanceUID=seriesInstanceUID, patient=None)

    def __str__(self):
        gs = self.gridSize
        s = 'Image2D '
        if not self.imageArray is None:
            s += str(self.imageArray.shape[0]) + 'x' +  str(self.imageArray.shape[1]) + '\n'
        return s

    # This is different from deepcopy because image can be a subclass of image2D but the method always returns an Image2D
    @classmethod
    def fromImage2D(cls, image, **kwargs):
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)
        return cls(**dic)

    @property
    def imageArray(self) -> np.ndarray:
        #return np.array(self._imageArray)
        return self._imageArray

    @imageArray.setter
    def imageArray(self, array:np.ndarray):
        self._imageArray = array

    @property
    def origin(self) -> np.ndarray:
        return self._origin

    @origin.setter
    def origin(self, origin):
        self._origin = np.array(origin)
        self.dataChangedSignal.emit()

    @property
    def spacing(self) -> np.ndarray:
        return self._spacing

    @spacing.setter
    def spacing(self, spacing):
        self._spacing = np.array(spacing)
        self.dataChangedSignal.emit()

    @property
    def angles(self) -> np.ndarray:
        return self._angles

    @angles.setter
    def angles(self, angles):
        self._angles = np.array(angles)
        self.dataChangedSignal.emit()

    @property
    def gridSize(self)  -> np.ndarray:
        if self.imageArray is None:
            return np.array((0, 0))

        return np.array(self.imageArray.shape)

    @property
    def gridSizeInWorldUnit(self) -> np.ndarray:
        return self.gridSize * self.spacing

    def getDataAtPosition(self, position:Sequence):
        voxelIndex = self.getVoxelIndexFromPosition(position)
        dataNumpy = self.imageArray[voxelIndex[0], voxelIndex[1]]

        return dataNumpy

    def getVoxelIndexFromPosition(self, position:Sequence[float]) -> Sequence[float]:
        positionInMM = np.array(position)
        shiftedPosInMM = positionInMM - self.origin
        posInVoxels = np.round(np.divide(shiftedPosInMM, self.spacing)).astype(np.int)

        return posInVoxels

    def getPositionFromVoxelIndex(self, index:Sequence[int]) -> Sequence[float]:
        return self.origin + np.array(index).astype(dtype=float)*self.spacing