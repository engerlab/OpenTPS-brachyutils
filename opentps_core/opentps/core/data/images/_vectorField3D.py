
__all__ = ['VectorField3D']


import numpy as np
import math
import copy
import logging

from opentps.core.data.images._image3D import Image3D
import opentps.core.processing.imageProcessing.resampler3D as resampler3D

logger = logging.getLogger(__name__)


class VectorField3D(Image3D):
    """
    Class for 3D vector fields. Inherits from Image3D.

    Attributes
    ----------
    name : str (default: "Vector Field")
        Name of the vector field.
    gridSize : tuple of int
        Size of the voxel grid.
    """

    def __init__(self, imageArray=None, name="Vector Field", origin=(0, 0, 0), spacing=(1, 1, 1),
                 angles=(0, 0, 0), seriesInstanceUID=None, patient=None):

        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles,
                         seriesInstanceUID=seriesInstanceUID, patient=patient)

    def __str__(self):
        return "Vector field: " + self.seriesInstanceUID

    # @classmethod --> this does nothing more than the parent class for now
    # def fromImage3D(cls, image: Image3D):
    #     return cls(imageArray=copy.deepcopy(image.imageArray), origin=image.origin, spacing=image.spacing, angles=image.angles, seriesInstanceUID=image.seriesInstanceUID)

    def copy(self):
        """
        Create a copy of the vector field.

        Returns
        -------
        VectorField3D
            Copy of the vector field.
        """
        return VectorField3D(imageArray=copy.deepcopy(self.imageArray), name=self.name+'_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID)

    def initFromImage(self, image):
        """
        Initialize vector field using the voxel grid of the input image.

        Parameters
        ----------
        image : Image3D
            image from which the voxel grid is copied.
        """

        # print('in vectorField3D initFromImage --> this if-fix is not ideal and should be changed. The issue comes from the gridSize which is a parameter ')
        # if image.__class__ == "CTImage":
        #     imgGridSize = image.gridSize
        # if image.__class__ == "CTImage":
        imgGridSize = image.gridSize
        self._imageArray = np.zeros((imgGridSize[0], imgGridSize[1], imgGridSize[2], 3))
        self.origin = image._origin
        self.spacing = image._spacing

    def warp(self, data, fillValue='closest', outputType=np.float32, tryGPU=True):
        """
        Warp 3D data using linear interpolation.

        Parameters
        ----------
        data : numpy array
            data to be warped.
        fillValue : scalar or 'closest' (default: 'closest')
            interpolation value for locations outside the input voxel grid. If 'closest', the closest voxel value is used.
        outputType : numpy type (default: np.float32)
            output data type.
        tryGPU : bool (default: True)
            if True, try to use GPU for warping.

        Returns
        -------
        numpy array
            Warped data.
        """

        return resampler3D.warp(data, self._imageArray, self.spacing, fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)

    def exponentiateField(self, outputType=np.float32, tryGPU=True):
        """
        Exponentiate the vector field (e.g. to convert velocity in to displacement).

        Parameters
        ----------
        outputType : numpy type (default: np.float32)
            output data type.
        tryGPU : bool (default: True)
            if True, try to use GPU for warping.

        Returns
        -------
        numpy array
            Displacement field.
        """

        norm = np.square(self._imageArray[:, :, :, 0]/self.spacing[0]) + np.square(self._imageArray[:, :, :, 1]/self.spacing[1]) + np.square(self._imageArray[:, :, :, 2]/self.spacing[2])
        N = math.ceil(2 + math.log2(np.maximum(1.0, np.amax(np.sqrt(norm)))) / 2) + 1
        if N < 1: N = 1

        displacement = self.copy()
        displacement._imageArray = displacement._imageArray * 2 ** (-N)

        for r in range(N):
            new_0 = displacement.warp(displacement._imageArray[:, :, :, 0], fillValue='closest', tryGPU=tryGPU)
            new_1 = displacement.warp(displacement._imageArray[:, :, :, 1], fillValue='closest', tryGPU=tryGPU)
            new_2 = displacement.warp(displacement._imageArray[:, :, :, 2], fillValue='closest', tryGPU=tryGPU)
            displacement._imageArray[:, :, :, 0] += new_0
            displacement._imageArray[:, :, :, 1] += new_1
            displacement._imageArray[:, :, :, 2] += new_2

        displacement._imageArray = displacement._imageArray.astype(outputType)

        return displacement

    def computeFieldNorm(self):
        """
        Compute the voxel-wise norm of the vector field.

        Returns
        -------
        numpy array
            Voxel-wise norm of the vector field.
        """
        return np.sqrt(
            self._imageArray[:, :, :, 0] ** 2 + self._imageArray[:, :, :, 1] ** 2 + self._imageArray[:, :, :, 2] ** 2)

    @property
    def gridSize(self):
        """
        Compute the voxel grid size of the deformation.

        Returns
        -------
        np.array
            Grid size of velocity field and/or displacement field.
        """

        return np.array([self._imageArray.shape[0:3]])[0]
