import pydicom
import numpy as np
import scipy.ndimage
import math
import logging

from Core.Processing.C_libraries.libInterp3_wrapper import Trilinear_Interpolation
from Core.Data.Images.image3D import Image3D

logger = logging.getLogger(__name__)


class VectorField3D(Image3D):

    def __init__(self, data=None, name="3D Vector Field", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1),
                 angles=(0, 0, 0), UID=""):

        super().__init__(data=data, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing, angles=angles,
                         UID=UID)

    def initFromImage(self, image):
        self.data = np.zeros(tuple(image.getGridSize()) + (3,))
        self.origin = image.origin
        self.spacing = image.spacing

    def warp(self, data, fillValue=0):
        size = data.shape

        if (self.data.shape[0:3] != size):
            logger.error("Image dimensions must match with the vector field to apply the displacement field.")
            return

        x = np.arange(size[0])
        y = np.arange(size[1])
        z = np.arange(size[2])
        xi = np.array(np.meshgrid(x, y, z))
        xi = np.rollaxis(xi, 0, 4)
        xi = xi.reshape((xi.size // 3, 3))
        xi = xi.astype('float32')
        xi[:, 0] += self.data[:, :, :, 0].transpose(1, 0, 2).reshape((xi.shape[0],))
        xi[:, 1] += self.data[:, :, :, 1].transpose(1, 0, 2).reshape((xi.shape[0],))
        xi[:, 2] += self.data[:, :, :, 2].transpose(1, 0, 2).reshape((xi.shape[0],))
        if fillValue == 'closest':
            xi[:, 0] = np.maximum(np.minimum(xi[:, 0], size[0] - 1), 0)
            xi[:, 1] = np.maximum(np.minimum(xi[:, 1], size[1] - 1), 0)
            xi[:, 2] = np.maximum(np.minimum(xi[:, 2], size[2] - 1), 0)
            fillValue = -1000
        # output = scipy.interpolate.interpn((x,y,z), data, xi, method='linear', fillValue=fillValue, bounds_error=False)
        output = Trilinear_Interpolation(data, size, xi, fillValue=fillValue)
        output = output.reshape((size[1], size[0], size[2])).transpose(1, 0, 2)

        return output

    def exponentiateField(self):
        norm = np.square(self.data[:, :, :, 0]) + np.square(self.data[:, :, :, 1]) + np.square(
            self.data[:, :, :, 2])
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

        return np.sqrt(
            self.data[:, :, :, 0] ** 2 + self.data[:, :, :, 1] ** 2 + self.data[:, :, :, 2] ** 2)
