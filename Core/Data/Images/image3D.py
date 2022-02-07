import copy
import numpy as np
import logging

from Core.Data.patientData import PatientData
import Core.Processing.ImageProcessing.resampler3D as resampler3D
from Core.event import Event

logger = logging.getLogger(__name__)


def euclidean_dist(v1, v2):
    return sum((p-q)**2 for p, q in zip(v1, v2)) ** .5


class Image3D(PatientData):
    def __init__(self, imageArray=None, name="3D Image", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), seriesInstanceUID=""):
        super().__init__(patientInfo=patientInfo, name=name, seriesInstanceUID=seriesInstanceUID)

        self.dataChangedSignal = Event()

        self._imageArray = imageArray
        self._origin = list(origin)
        self._spacing = list(spacing)
        self._angles = list(angles)
        # if UID is None:
        #     UID = generate_uid()
        # self.UID = UID

    def __str__(self):
        gs = self.gridSize
        s = 'Image3D ' + str(gs[0]) + ' x ' +  str(gs[1]) +  ' x ' +  str(gs[2]) + '\n'
        return s

    def copy(self):
        img = copy.deepcopy(self)
        # img.name = img.name + '_copy'
        return img

    @property
    def imageArray(self):
        return self._imageArray

    @imageArray.setter
    def imageArray(self, array):
        self._imageArray = array
        self.dataChangedSignal.emit()

    @property
    def origin(self):
        return self._origin

    @origin.setter
    def origin(self, origin):
        self._origin = list(origin)
        self.dataChangedSignal.emit()

    @property
    def spacing(self):
        return self._spacing

    @spacing.setter
    def spacing(self, spacing):
        self._spacing = list(spacing)
        self.dataChangedSignal.emit()

    @property
    def angles(self):
        return self._angles

    @angles.setter
    def angles(self, angles):
        self._angles = list(angles)
        self.dataChangedSignal.emit()

    @property
    def gridSize(self):
        """Compute the voxel grid size of the image.

            Returns
            -------
            list
                Image grid size.
            """

        if self._imageArray is None:
            return (0, 0, 0)
        elif np.size(self._imageArray) == 0:
            return (0, 0, 0)
        return self._imageArray.shape[0:3]


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

        if (self.gridSize == otherImage.gridSize and
                euclidean_dist(self._origin, otherImage._origin) < 0.01 and
                euclidean_dist(self._spacing, otherImage._spacing) < 0.01):
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

        self._imageArray = resampler3D.resample(self._imageArray, self._origin, self._spacing, list(self.gridSize), origin, spacing, gridSize, fillValue=fillValue, outputType=outputType)
        self._origin = list(origin)
        self._spacing = list(spacing)

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
            self.resample(otherImage.gridSize, otherImage._origin, otherImage._spacing, fillValue=fillValue, outputType=outputType)