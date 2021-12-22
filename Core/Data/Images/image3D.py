import copy
import numpy as np
import logging

from Core.Data.patientData import PatientData
import Core.Processing.ImageProcessing.resampler3D as resampler3D

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
        s = 'Image3D ' + str(gs[0]) + ' x ' +  str(gs[1]) +  ' x ' +  str(gs[2]) + '\n'
        return s

    def getGridSize(self):
        if self.data is None:
            return (0, 0, 0)
        elif np.size(self.data) == 0:
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

    def resample(self, gridSize, origin, spacing, fillValue=0, outputType=None):
        self.data = resampler3D.resample(self.data,self.origin,self.spacing,list(self.getGridSize()),origin,spacing,gridSize,fillValue=fillValue,outputType=outputType)
        self.origin = list(origin)
        self.spacing = list(spacing)

    def resampleToImageGrid(self, image, fillValue=0, outputType=None):
        if (not image.hasSameGrid(self)):
            logger.info('Resample field to CT grid.')
            self.resample(image.getGridSize(),image.origin,image.spacing,fillValue=fillValue,outputType=outputType)
