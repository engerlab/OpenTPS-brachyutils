
__all__ = ['Transform3D']


import logging
import copy
from opentps.core.data._patientData import PatientData

logger = logging.getLogger(__name__)


class Transform3D(PatientData):

    def __init__(self, tform=None, name="Transform", center=None):
        super().__init__(name=name)

        self.tform = tform
        self.name = name
        self.center = center

    def copy(self):
        return Transform3D(tform=copy.deepcopy(self.tform), name=self.name + '_copy', center=self.center)

    def setMatrix4x4(self, tform):
        self.tform = tform

    def setCenter(self, center):
        self.center = center

    def deformImage(self, image, fillValue=-1000):
        """Transform 3D image using linear interpolation.

            Parameters
            ----------
            image :
                image to be deformed.
            fillValue : scalar
                interpolation value for locations outside the input voxel grid.

            Returns
            -------
                Deformed image.
            """

        image = image.copy()

        if fillValue=='closest':
            fillValue = float(image.min())

        try:
            from opentps.core.processing.imageProcessing import sitkImageProcessing
            sitkImageProcessing.applyTransform(image, self.tform, fillValue, centre = self.center)
        except:
            logger.info('Failed to use SITK transform. Abort.')

        return image
