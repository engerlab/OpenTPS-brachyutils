
__all__ = ['Transform3D']


import logging
import copy
import math as m

import numpy as np

from opentps.core.data._patientData import PatientData
from opentps.core.processing.imageProcessing.imageTransform3D import transform3DMatrixFromTranslationAndRotationsVectors, applyTransform3D, translateDataByChangingOrigin

logger = logging.getLogger(__name__)


class Transform3D(PatientData):

    def __init__(self, tformMatrix=None, name="Transform", rotCenter='imgCenter'):
        super().__init__(name=name)

        self.tformMatrix = tformMatrix
        self.name = name
        self.rotCenter = rotCenter

    def copy(self):
        return Transform3D(tformMatrix=copy.deepcopy(self.tformMatrix), name=self.name + '_copy', rotCenter=self.rotCenter)

    def setMatrix4x4(self, tformMatrix):
        self.tformMatrix = tformMatrix

    def setCenter(self, center):
        self.rotCenter = center

    def deformImage(self, data, fillValue=0, outputBox='keepAll', tryGPU=False):
        """Transform 3D image using linear interpolation.

            Parameters
            ----------
            data :
                image to be deformed.
            fillValue : scalar
                interpolation value for locations outside the input voxel grid.

            Returns
            -------
                Deformed image.
            """

        data = data.copy()

        if fillValue == 'closest':
            fillValue = float(data.min())

        applyTransform3D(data, self.tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=self.rotCenter, tryGPU=tryGPU)

        return data

    def deformData(self, data, fillValue=0, outputBox='keepAll', tryGPU=False, interpOrder=1):
        """Transform 3D image using linear interpolation.

            Parameters
            ----------
            data :
                image to be deformed.
            fillValue : scalar
                interpolation value for locations outside the input voxel grid.

            Returns
            -------
                Deformed image.
            """

        data = data.copy()

        if fillValue == 'closest':
            fillValue = float(data.min())

        if np.array(self.getRotationAngles() == np.array([0, 0, 0])).all() and outputBox == 'keepAll':
            translateDataByChangingOrigin(data, self.getTranslation())
        else:
            applyTransform3D(data, self.tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=self.rotCenter, tryGPU=tryGPU, interpOrder=interpOrder)

        return data
      
    def getRotationAngles(self, inDegrees=False):
        """Returns the Euler angles in radians.
        
            Returns
            -------                
                list of 3 floats: the Euler angles in radians (Rx,Ry,Rz).
            """
            
        R = self.tformMatrix[0:-1, 0:-1]
        eul1 = m.atan2(R.item(1, 0), R.item(0, 0))
        sp = m.sin(eul1)
        cp = m.cos(eul1)
        eul2 = m.atan2(-R.item(2, 0), cp * R.item(0, 0) + sp * R.item(1, 0))
        eul3 = m.atan2(sp * R.item(0, 2) - cp * R.item(1, 2), cp * R.item(1, 1) - sp * R.item(0, 1))

        angleArray = np.array([eul3, eul2, eul1])

        if inDegrees:
            angleArray *= 180/np.pi

        return -angleArray
         
    def getTranslation(self):
        """Returns the translation.
        
            Returns
            -------                
                list of 3 floats: the translation in the 3 directions [Tx,Ty,Tz].
            """
        return -self.tformMatrix[0:-1, -1]

    def initFromTranslationAndRotationVectors(self, transVec=[0, 0, 0], rotVec=[0, 0, 0]):
        """

        Parameters
        ----------
        translation
        rotation

        Returns
        -------

        """
        self.tformMatrix = transform3DMatrixFromTranslationAndRotationsVectors(transVec=transVec, rotVec=rotVec)
