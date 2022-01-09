import numpy as np
import math
import logging

from Core.Data.Images.image3D import Image3D
import Core.Processing.ImageProcessing.resampler3D as resampler3D

logger = logging.getLogger(__name__)


class VectorField3D(Image3D):

    def __init__(self, data=None, name="Vector Field", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1),
                 angles=(0, 0, 0), seriesInstanceUID=""):

        super().__init__(data=data, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing, angles=angles,
                         seriesInstanceUID=seriesInstanceUID)

    def initFromImage(self, image):
        """Initialize vector field using the voxel grid of the input image.

            Parameters
            ----------
            image : numpy array
                image from which the voxel grid is copied.
            """

        self.data = np.zeros(tuple(image.getGridSize()) + (3,))
        self.origin = image.origin
        self.spacing = image.spacing

    def warp(self, data, fillValue=0):
        """Warp 3D data using linear interpolation.

        Parameters
        ----------
        data : numpy array
            data to be warped.
        fillValue : scalar
            interpolation value for locations outside the input voxel grid.

        Returns
        -------
        numpy array
            Warped data.
        """

        return resampler3D.warp(data,self.data,self.spacing,fillValue=fillValue)

    def exponentiateField(self):
        """Exponentiate the vector field (e.g. to convert velocity in to displacement).

        Returns
        -------
        numpy array
            Displacement field.
        """

        norm = np.square(self.data[:, :, :, 0]/self.spacing[0]) + np.square(self.data[:, :, :, 1]/self.spacing[1]) + np.square(self.data[:, :, :, 2]/self.spacing[2])
        N = math.ceil(2 + math.log2(np.maximum(1.0, np.amax(np.sqrt(norm)))) / 2) + 1
        if N < 1: N = 1

        displacement = self.copy()
        displacement.data = displacement.data * 2 ** (-N)

        for r in range(N):
            new_0 = displacement.warp(displacement.data[:, :, :, 0], fillValue=0)
            new_1 = displacement.warp(displacement.data[:, :, :, 1], fillValue=0)
            new_2 = displacement.warp(displacement.data[:, :, :, 2], fillValue=0)
            displacement.data[:, :, :, 0] += new_0
            displacement.data[:, :, :, 1] += new_1
            displacement.data[:, :, :, 2] += new_2

        return displacement

    def computeFieldNorm(self):
        """Compute the voxel-wise norm of the vector field.

        Returns
        -------
        numpy array
            Voxel-wise norm of the vector field.
        """
        return np.sqrt(
            self.data[:, :, :, 0] ** 2 + self.data[:, :, :, 1] ** 2 + self.data[:, :, :, 2] ** 2)
