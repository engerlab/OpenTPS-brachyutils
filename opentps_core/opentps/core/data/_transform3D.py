
__all__ = ['Transform3D']


import logging
import copy
import math as m

import numpy as np

from opentps.core.data._patientData import PatientData
from opentps.core.processing.imageProcessing.imageTransform3D import transform3DMatrixFromTranslationAndRotationsVectors

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

        if fillValue == 'closest':
            fillValue = float(image.min())

        try:
            from opentps.core.processing.imageProcessing import sitkImageProcessing
            sitkImageProcessing.applyTransform(image, self.tform, fillValue, centre=self.center)
        except:
            logger.info('Failed to use SITK transform. Abort.')

        return image
      
    def getRotationAngles(self, inDegrees=False):
        """Returns the Euler angles in radians.
        
            Returns
            -------                
                list of 3 floats: the Euler angles in radians (Rx,Ry,Rz).
            """
            
        R = self.tform[0:-1, 0:-1]
        eul1 = m.atan2(R.item(1, 0), R.item(0, 0))
        sp = m.sin(eul1)
        cp = m.cos(eul1)
        eul2 = m.atan2(-R.item(2, 0), cp * R.item(0, 0) + sp * R.item(1, 0))
        eul3 = m.atan2(sp * R.item(0, 2) - cp * R.item(1, 2), cp * R.item(1, 1) - sp * R.item(0, 1))

        angleArray = np.array([eul3, eul2, eul1])

        if inDegrees:
            angleArray *= 180/np.pi

        return angleArray
         
    def getTranslation(self):
        """Returns the translation.
        
            Returns
            -------                
                list of 3 floats: the translation in the 3 directions [Tx,Ty,Tz].
            """
        return self.tform[0:-1, -1]

    def initFromTranslationAndRotationVectors(self, translation, rotation):
        """

        Parameters
        ----------
        translation
        rotation

        Returns
        -------

        """
        self.tform = transform3DMatrixFromTranslationAndRotationsVectors(translation, rotation)