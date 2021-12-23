import copy
import numpy as np
import logging
from pydicom.uid import generate_uid

from Core.Data.patientData import PatientData
import Core.Processing.ImageProcessing.resampler3D as resampler3D

logger = logging.getLogger(__name__)


def euclidean_dist(v1, v2):
    return sum((p-q)**2 for p, q in zip(v1, v2)) ** .5


class Image3D(PatientData):
    def __init__(self, data=None, name="3D Image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), UID=None):
        super().__init__(patientInfo=patientInfo)
        self.data = data
        self.name = name
        self.origin = list(origin)
        self.spacing = list(spacing)
        self.angles = list(angles)
        if UID is None:
            UID = generate_uid()
        self.UID = UID

    def __str__(self):
        gs = self.getGridSize()
        s = 'Image3D ' + str(gs[0]) + ' x ' +  str(gs[1]) +  ' x ' +  str(gs[2]) + '\n'
        return s

    def copy(self):
        img = copy.deepcopy(self)
        img.name = img.name + '_copy'
        return img

    def getGridSize(self):
        """Compute the voxel grid size of the image.

            Returns
            -------
            list
                Image grid size.
            """

        if self.data is None:
            return (0, 0, 0)
        elif np.size(self.data) == 0:
            return (0, 0, 0)
        return self.data.shape[0:3]


    def hasSameGrid(self, otherImage):
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

        if (self.getGridSize() == otherImage.getGridSize() and
                euclidean_dist(self.origin, otherImage.origin) < 0.01 and 
                euclidean_dist(self.spacing, otherImage.spacing) < 0.01):
            return True
        else:
            return False

    def resample(self, gridSize, origin, spacing, fillValue=0, outputType=None):
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

        self.data = resampler3D.resample(self.data,self.origin,self.spacing,list(self.getGridSize()),origin,spacing,gridSize,fillValue=fillValue,outputType=outputType)
        self.origin = list(origin)
        self.spacing = list(spacing)

    def resampleToImageGrid(self, otherImage, fillValue=0, outputType=None):
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
            logger.info('Resample field to CT grid.')
            self.resample(otherImage.getGridSize(),otherImage.origin,otherImage.spacing,fillValue=fillValue,outputType=outputType)
