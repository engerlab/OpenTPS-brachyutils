
__all__ = ['Image3D']


import copy
from typing import Sequence

import numpy as np
import logging
# from core.data.images.vectorField3D import VectorField3D

from opentps.core.data._patientData import PatientData
from opentps.core import Event
import pydicom

logger = logging.getLogger(__name__)


def euclidean_dist(v1, v2):
    """
    Compute the euclidean distance between two vectors.

    Parameters
    ----------
    v1 : numpy array
        First vector.
    v2 : numpy array
        Second vector.

    Returns
    -------
    float
        Euclidean distance between the two vectors.
    """
    return sum((p-q)**2 for p, q in zip(v1, v2)) ** .5


class Image3D(PatientData):
    """
    Class for 3D images. Inherits from PatientData and its attributes.

    Attributes
    ----------
    name : str (default: '3D Image')
        Name of the image.
    imageArray : numpy array
        3D array containing the image data.
    origin : numpy array (default: (0, 0, 0))
        3D array containing the origin of the image.
    spacing : numpy array (default: (1, 1, 1))
        3D array containing the spacing of the image.
    angles : numpy array (default: (0, 0, 0))
        3D array containing the angles of the image.
    gridSize : numpy array
        3D array containing the grid size of the image.
    gridSizeInWorldUnit : numpy array
        3D array containing the grid size of the image in world units.
    numberOfVoxels : int
        Number of voxels in the image.
    """
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
        """
        Create a new Image3D from an existing Image3D.

        Parameters
        ----------
        image : Image3D
            Image to copy.
        kwargs : dict (optional)
            Additional keyword arguments to pass to the constructor.
                - imageArray : numpy.ndarray
                    Image array of the image.
                - origin : tuple of float
                    Origin of the image.
                - spacing : tuple of float
                    Spacing of the image.
                - angles : tuple of float
                    Angles of the image.
                - seriesInstanceUID : str
                    Series instance UID of the image.
                - patient : Patient
                    Patient object of the image.

        Returns
        -------
        Image3D
            New Image3D object.
        """
        dic = {'imageArray': copy.deepcopy(image.imageArray), 'origin': image.origin, 'spacing': image.spacing,
               'angles': image.angles, 'seriesInstanceUID': image.seriesInstanceUID, 'patient': image.patient, 'name': image.name}
        dic.update(kwargs)
        return cls(**dic)

    def copy(self):
        """
        Create a copy of the image.

        Returns
        -------
        Image3D
            Copy of the image.
        """
        return Image3D(imageArray=copy.deepcopy(self.imageArray), name=self.name + '_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=pydicom.uid.generate_uid())

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
        resampleImage3D(self, spacing=spacing, gridSize=gridSize, origin=origin, fillValue=fillValue, tryGPU=tryGPU, inPlace=True, outputType=outputType)

    def getDataAtPosition(self, position: Sequence):
        """
        Get the data value of the image array at a given position in the image.

        Parameters
        ----------
        position : Sequence
            Position in the image.

        Returns
        -------
        np.ndarray
            Data value of the image array at the given position.
        """
        voxelIndex = self.getVoxelIndexFromPosition(position)
        dataNumpy = self.imageArray[voxelIndex[0], voxelIndex[1], voxelIndex[2]]

        return dataNumpy

    def getVoxelIndexFromPosition(self, position:Sequence[float]) -> Sequence[float]:
        """
        Get the voxel index of the image array at a given position in the image.

        Parameters
        ----------
        position : Sequence[float]
            Position in the image.

        Returns
        -------
        Sequence[float]
            Voxel index of the image array at the given position.
        """
        positionInMM = np.array(position)
        shiftedPosInMM = positionInMM - self.origin
        posInVoxels = np.round(np.divide(shiftedPosInMM, self.spacing)).astype(int)
        if np.any(np.logical_or(posInVoxels < 0, posInVoxels > (self.gridSize - 1))):
            raise ValueError('Voxel position requested is outside of the domain of the image')

        return posInVoxels

    def getPositionFromVoxelIndex(self, index:Sequence[int]) -> Sequence[float]:
        """
        Get the position in the image from a given voxel index.

        Parameters
        ----------
        index : Sequence[int]
            Voxel index in the image.

        Returns
        -------
        Sequence[float]
            Position in the image from the given voxel index.
        """
        index = np.array(index)
        if np.any(np.logical_or(index < 0, index > (self.gridSize - 1))):
            raise ValueError('Voxel position requested is outside of the domain of the image')
        return self.origin + np.array(index).astype(dtype=float)*self.spacing

    def getMeshGridPositions(self) -> np.ndarray:
        """
        Get the mesh grid positions of the image in mm.

        Returns
        -------
        np.ndarray
            Mesh grid positions of the image in mm.
        """
        x = self.origin[0] + np.arange(self.gridSize[0]) * self.spacing[0]
        y = self.origin[1] + np.arange(self.gridSize[1]) * self.spacing[1]
        z = self.origin[2] + np.arange(self.gridSize[2]) * self.spacing[2]
        return np.meshgrid(x,y,z, indexing='ij')

    def min(self):
        """
        Get the minimum value of the image array.

        Returns
        -------
        float
            Minimum value of the image array.
        """
        return self._imageArray.min()

    def max(self):
        """
        Get the maximum value of the image array.

        Returns
        -------
        float
            Maximum value of the image array.
        """
        return self._imageArray.max()

    def compressData(self):
        """
        Changes pixel type of data imageArray to int16 for more efficient storage
        """
        self.imageArray = self.imageArray.astype(np.int16)