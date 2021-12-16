import copy
import numpy as np
import scipy.ndimage
import logging

from Core.Processing.C_libraries.libInterp3_wrapper import Trilinear_Interpolation
from Core.Data.patientData import PatientData

logger = logging.getLogger(__name__)


def euclidean_dist(v1, v2):
    return sum((p-q)**2 for p, q in zip(v1, v2)) ** .5


class Image3D(PatientData):
    def __init__(self, data=None, name="3D Image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), UID=""):
        super().__init__(patientInfo=patientInfo)
        self.data = data
        self.name = name
        self.origin = origin
        self.spacing = spacing
        self.angles = angles
        self.UID = UID


    def __str__(self):
        gs = self.getGridSize()
        s = 'Image3D ' + str(gs[0]) + 'x' +  str(gs[1]) + '\n'
        return s

    def getGridSize(self):
        if self.data is None:
            return (0, 0, 0)

        return self.data.shape[0:3]

    def copy(self):
        img = copy.deepcopy(self)
        img.name = img.name + '_copy'
        return img

    def hasSameGrid(self, otherImage):
        if (self.getGridSize() == otherImage.getGridSize() and 
                euclidean_dist(self.origin, otherImage.origin) < 0.01 and 
                euclidean_dist(self.spacing, otherImage.spacing) < 0.01):
            return True
        else:
            return False

    def resample(self, gridSize, origin, spacing, fillValue=0):
        vectorDimension = 1
        if self.data.ndim > 3:
            vectorDimension = self.data.shape[3]

        # anti-aliasing filter
        sigma = [0, 0, 0]
        if (spacing[0] > self.spacing[0]): sigma[0] = 0.4 * (spacing[0] / self.spacing[0])
        if (spacing[1] > self.spacing[1]): sigma[1] = 0.4 * (spacing[1] / self.spacing[1])
        if (spacing[2] > self.spacing[2]): sigma[2] = 0.4 * (spacing[2] / self.spacing[2])
        if (sigma != [0, 0, 0]):
            logger.info("Field is filtered before downsampling")
            if vectorDimension > 1:
                for i in range(vectorDimension):
                    self.data[:, :, :, i] = scipy.ndimage.gaussian_filter(self.data[:, :, :, i], sigma)
            else:
                self.data[:, :, :] = scipy.ndimage.gaussian_filter(self.data[:, :, :], sigma)

        # resampling
        initGridSize = list(self.getGridSize())

        interpX = (origin[0] - self.origin[0] + np.arange(gridSize[0]) * spacing[0]) / \
                  self.spacing[0]
        interpY = (origin[1] - self.origin[1] + np.arange(gridSize[1]) * spacing[1]) / \
                  self.spacing[1]
        interpZ = (origin[2] - self.origin[2] + np.arange(gridSize[2]) * spacing[2]) / \
                  self.spacing[2]

        # Correct for potential precision issues on the border of the grid
        interpX[interpX > initGridSize[0] - 1] = np.round(interpX[interpX > initGridSize[0] - 1] * 1e3) / 1e3
        interpY[interpY > initGridSize[1] - 1] = np.round(interpY[interpY > initGridSize[1] - 1] * 1e3) / 1e3
        interpZ[interpZ > initGridSize[2] - 1] = np.round(interpZ[interpZ > initGridSize[2] - 1] * 1e3) / 1e3

        xi = np.array(np.meshgrid(interpX, interpY, interpZ))
        xi = np.rollaxis(xi, 0, 4)
        xi = xi.reshape((xi.size // 3, 3))

        if vectorDimension > 1:
            field = np.zeros((*gridSize, vectorDimension))
            for i in range(vectorDimension):
                fieldTemp = Trilinear_Interpolation(self.data[:, :, :, i], initGridSize, xi, fillValue=fillValue)
                field[:, :, :, i] = fieldTemp.reshape((gridSize[1], gridSize[0], gridSize[2])).transpose(1, 0, 2) * self.spacing[i] / spacing[i]
            self.data = field
        else:
            self.data = Trilinear_Interpolation(self.data, initGridSize, xi, fillValue=fillValue)
            self.data = self.data.reshape((gridSize[1], gridSize[0], gridSize[2])).transpose(1, 0, 2)

        self.origin = list(origin)
        self.spacing = list(spacing)

    def resampleToCTGrid(self, ct, fillValue=0):
        if (not ct.hasSameGrid(self)):
            logger.info('Resample field to CT grid.')
            self.resample(ct.getGridSize(), ct.origin, ct.spacing, fillValue=fillValue)
