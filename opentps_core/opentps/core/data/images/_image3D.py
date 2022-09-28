
__all__ = ['Image3D']


import copy
from typing import Sequence

import numpy as np
import logging
# from core.data.images.vectorField3D import VectorField3D

from opentps.core.data._patientData import PatientData
from opentps.core import Event

logger = logging.getLogger(__name__)


def euclidean_dist(v1, v2):
    return sum((p-q)**2 for p, q in zip(v1, v2)) ** .5


class Image3D(PatientData):
    def __init__(self, imageArray=None, name="3D Image", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), seriesInstanceUID=None, patient=None):
        self.dataChangedSignal = Event()

        self._imageArray = imageArray
        self._origin = np.array(origin)
        self._spacing = np.array(spacing)
        self._angles = np.array(angles)
        # if UID is None:
        #     UID = generate_uid()
        # self.UID = UID

        super().__init__(name=name, seriesInstanceUID=seriesInstanceUID,
                         patient=patient)  # We want to trigger super signal only when the object is fully initialized

    def __str__(self):
        gs = self.gridSize
        s = 'Image3D ' + str(gs[0]) + ' x ' +  str(gs[1]) +  ' x ' +  str(gs[2]) + '\n'
        return s

    # This is different from deepcopy because image can be a subclass of image3D but the method always returns an Image3D
    @classmethod
    def fromImage3D(cls, image, **kwargs):
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient}
        dic.update(kwargs)
        return cls(**dic)

    def copy(self):
        return Image3D(imageArray=copy.deepcopy(self.imageArray), name=self.name + '_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID)

    @property
    def imageArray(self) -> np.ndarray:
        #return np.array(self._imageArray)
        return self._imageArray

    @imageArray.setter
    def imageArray(self, array):
        if not (array is None):
            logger.debug("Array " + str(array.shape))
        self._imageArray = array
        self.dataChangedSignal.emit()

    def update(self):
        self.dataChangedSignal.emit()

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
    def gridSize(self) -> np.ndarray:
        """Compute the voxel grid size of the image.

            Returns
            -------
            np.array
                Image grid size.
            """
        if self._imageArray is None:
            return np.array([0, 0, 0])
        elif np.size(self._imageArray) == 0:
            return np.array([0, 0, 0])
        return np.array(self._imageArray.shape)

    @property
    def gridSizeInWorldUnit(self)  -> np.ndarray:
        return self.gridSize*self.spacing


    def hasSameGrid(self, otherImage) -> bool:
        """Check whether the voxel grid is the same as the voxel grid of another image given as input.

            Parameters
            ----------
            otherImage : numpy array
                image to which the voxel grid is compared.

            Returns
            -------
            bool
                True if grids are identical, False otherwise.
            """

        if (np.array_equal(self.gridSize, otherImage.gridSize) and
                np.allclose(self._origin, otherImage._origin, atol=0.01) and
                np.allclose(self._spacing, otherImage.spacing, atol=0.01)):
            return True
        else:
            return False

    @property
    def numberOfVoxels(self):
        return self.gridSize[0] * self.gridSize[1] * self.gridSize[2]

    def resampleOn(self, otherImage, fillValue=0, outputType=None, tryGPU=True):
        """Resample image using the voxel grid of another image given as input, using linear interpolation.

            Parameters
            ----------
            otherImage : numpy array
                image from which the voxel grid is copied.
            fillValue : scalar
                interpolation value for locations outside the input voxel grid.
            outputType : numpy data type
                type of the output.
            """

        if (not otherImage.hasSameGrid(self)):
            logger.info('Resample to image grid.')
            self.resample(otherImage.spacing, otherImage.gridSize, otherImage.origin, fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)

    def resample(self, spacing, gridSize, origin, fillValue=0, outputType=None, tryGPU=True):
        """Resample image according to new voxel grid using linear interpolation.

            Parameters
            ----------
            gridSize : list
                size of the resampled image voxel grid.
            origin : list
                origin of the resampled image voxel grid.
            spacing : list
                spacing of the resampled image voxel grid.
            fillValue : scalar
                interpolation value for locations outside the input voxel grid.
            outputType : numpy data type
                type of the output.
            """

        from opentps.core.processing.imageProcessing.resampler3D import resampleImage3D
        resampleImage3D(self, spacing, gridSize, origin, fillValue=fillValue, tryGPU=tryGPU, inPlace=True)

    def getDataAtPosition(self, position: Sequence):
        voxelIndex = self.getVoxelIndexFromPosition(position)
        dataNumpy = self.imageArray[voxelIndex[0], voxelIndex[1], voxelIndex[2]]

        return dataNumpy

    def getVoxelIndexFromPosition(self, position:Sequence[float]) -> Sequence[float]:
        positionInMM = np.array(position)
        shiftedPosInMM = positionInMM - self.origin
        posInVoxels = np.round(np.divide(shiftedPosInMM, self.spacing)).astype(np.int)

        return posInVoxels

    def getPositionFromVoxelIndex(self, index:Sequence[int]) -> Sequence[float]:
        return self.origin + np.array(index).astype(dtype=float)*self.spacing

    def min(self):
        return self._imageArray.min()

    def max(self):
        return self._imageArray.max()
