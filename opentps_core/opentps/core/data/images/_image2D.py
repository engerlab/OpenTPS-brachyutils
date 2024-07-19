
__all__ = ['Image2D']


import copy
from typing import Sequence

import numpy as np

from opentps.core.data._patientData import PatientData
from opentps.core import Event


class Image2D(PatientData):
    """
    Class for 2D images. Inherits from PatientData.

    Attributes
    ----------
    name : str (default: "2D Image")
        Name of the image.
    imageArray : numpy array
        2D numpy array containing the image data.
    origin : numpy array (default: (0,0,0))
        1x3 numpy array containing the origin of the image.
    spacing : numpy array (default: (1,1))
        1x2 numpy array containing the spacing of the image in mm.
    angles : numpy array (default: (0,0,0))
        1x3 numpy array containing the angles of the image.
    gridSize : numpy array
        1x2 numpy array containing the size of the image in voxels.
    gridSizeInWorldUnit : numpy array
        1x2 numpy array containing the size of the image in mm.
    """
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
        """
        Creates a new Image2D from an existing Image2D.

        Parameters
        ----------
        image : Image2D
            Image2D to copy.
        kwargs : dict (optional)
            Keyword arguments to be passed to the constructor.
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
        """
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
        """
        Returns the data from the image array at a given position in the image.

        Parameters
        ----------
        position : tuple of float
            Position in the image in mm.

        Returns
        -------
        dataNumpy : numpy.ndarray
            Data from the image array at the given position.
        """
        voxelIndex = self.getVoxelIndexFromPosition(position)
        dataNumpy = self.imageArray[voxelIndex[0], voxelIndex[1]]

        return dataNumpy

    def getVoxelIndexFromPosition(self, position:Sequence[float]) -> Sequence[float]:
        """
        Returns the voxel index of a given position in the image.

        Parameters
        ----------
        position : tuple of float
            Position in the image in mm.

        Returns
        -------
        voxelIndex : tuple of int
            Voxel index of the given position.

        Raises
        ------
        ValueError
            If the voxel index is outside of the image.
        """
        positionInMM = np.array(position)
        shiftedPosInMM = positionInMM - self.origin
        posInVoxels = np.round(np.divide(shiftedPosInMM, self.spacing)).astype(int)
        if np.any(np.logical_or(posInVoxels < 0, posInVoxels > (self.gridSize - 1))):
            raise ValueError('Voxel position requested is outside of the domain of the image')

        return posInVoxels

    def getPositionFromVoxelIndex(self, index:Sequence[int]) -> Sequence[float]:
        """
        Returns the position in the image of a given voxel index.

        Parameters
        ----------
        index : tuple of int
            Voxel index in the image.

        Returns
        -------
        position : tuple of float
            Position in the image in mm.

        Raises
        ------
        ValueError
            If the voxel index is outside of the image.
        """
        if np.any(np.logical_or(index < 0, index > (self.gridSize - 1))):
            raise ValueError('Voxel position requested is outside of the domain of the image')
        return self.origin + np.array(index).astype(dtype=float)*self.spacing

    def getMeshGridPositions(self) -> np.ndarray:
        """
        Returns the meshgrid of the image in mm.

        Returns
        -------
        meshgrid : numpy.ndarray
            Meshgrid of the image in mm.
        """
        x = self.origin[0] + np.arange(self.gridSize[0]) * self.spacing[0]
        y = self.origin[1] + np.arange(self.gridSize[1]) * self.spacing[1]
        return np.meshgrid(x,y, indexing='ij')

    def hasSameGrid(self, otherImage) -> bool:
        """
        Check whether the voxel grid is the same as the voxel grid of another image given as input.

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

    def copy(self):
        """
        Create a copy of the image.

        Returns
        -------
        Image3D
            Copy of the image.
        """
        return Image2D(imageArray=copy.deepcopy(self.imageArray), name=self.name + '_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID)

    def compressData(self):
        """
        Changes pixel type of data imageArray to int16 for more efficient storage
        """
        self.imageArray = self.imageArray.astype(np.int16)
