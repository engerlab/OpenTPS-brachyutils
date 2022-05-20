from typing import Sequence

import numpy as np

from Core.Data.patientData import PatientData
from Core.event import Event


class Image2D(PatientData):
    def __init__(self, imageArray=None, name="2D Image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1), angles=(0, 0, 0), seriesInstanceUID=""):
        super().__init__(patientInfo=patientInfo, name=name, seriesInstanceUID=seriesInstanceUID)

        self.dataChangedSignal = Event()

        self.imageArray:np.ndarray = imageArray
        self._origin = np.array(origin)
        self._spacing = np.array(spacing)
        self._angles = np.array(angles)

    def __str__(self):
        gs = self.gridSize
        s = 'Image2D ' + str(self.imageArray.shape[0]) + 'x' +  str(self.imageArray.shape[1]) + '\n'
        return s

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