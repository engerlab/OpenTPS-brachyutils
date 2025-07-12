
__all__ = ['Transform3D']


import logging
import copy
import math as m

import numpy as np

from opentps.core.data._patientData import PatientData
from opentps.core.processing.imageProcessing.imageTransform3D import transform3DMatrixFromTranslationAndRotationsVectors, applyTransform3D, translateDataByChangingOrigin

logger = logging.getLogger(__name__)


class Transform3D(PatientData):
    """
    Class for 3D transformations. Inherits from PatientData.

    Attributes
    ----------
    tformMatrix : 4x4 numpy array
        transformation matrix.
    name : string
        name of the transformation.
    rotCenter : string
        center of rotation, can be 'imgCenter' or 'origin'.
    """

    def __init__(self, tformMatrix=None, name="Transform", rotCenter='imgCenter'):
        super().__init__(name=name)

        self.tformMatrix = tformMatrix
        self.name = name
        self.rotCenter = rotCenter

    def copy(self):
        """
        Returns a copy of the Transform3D object.

        Returns
        -------
        Transform3D
            Copy of the Transform3D object.
        """
        return Transform3D(tformMatrix=copy.deepcopy(self.tformMatrix), name=self.name + '_copy', rotCenter=self.rotCenter)

    def setMatrix4x4(self, tformMatrix):
        """
        Sets the transformation matrix.
        """
        self.tformMatrix = tformMatrix

    def setCenter(self, center):
        """
        Sets the center of rotation.
        """
        self.rotCenter = center

    def deformImage(self, data, fillValue=0, outputBox='keepAll', tryGPU=False):
        """
        Transform 3D image using linear interpolation.

        Parameters
        ----------
        data :
            image to be deformed.
        fillValue : scalar or 'closest' (default: 0)
            interpolation value for locations outside the input voxel grid. If 'closest', the closest voxel value will
            be used.
        outputBox : string or list of 6 floats (default: 'keepAll')
            'keepAll' or 'same' or [xMin, xMax, yMin, yMax, zMin, zMax]. If 'keepAll', the output image will be large
            enough to contain the entire input image. If 'same', the output image will have the same size and origin as the input
            image. If a list of 6 floats, the output image will have the specified size.

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
        """
        Transform 3D image using linear interpolation.

        Parameters
        ----------
        data :
            image to be deformed.
        fillValue : scalar or 'closest' (default: 0)
            interpolation value for locations outside the input voxel grid. If 'closest', the closest voxel value will
            be used.
        outputBox : string or list of 6 floats (default: 'keepAll')
            'keepAll' or 'same' or [xMin, xMax, yMin, yMax, zMin, zMax]. If 'keepAll', the output image will be large
            enough to contain the entire input image. If 'same', the output image will have the same size and origin as the input
            image. If a list of 6 floats, the output image will have the specified size.
        tryGPU : bool (default: False)
            if True, the GPU will be used if available.
        interpOrder : int (default: 1)
            order of the interpolation. 0 for nearest neighbor, 1 for linear, 3 for cubic.

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
        """
        Returns the Euler angles in radians.

        Parameters
        ----------
        inDegrees : bool (default: False)
            if True, the angles will be returned in degrees.
        
        Returns
        -------
        list of 3 floats
            The Euler angles in radians (Rx,Ry,Rz).
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
        """
        Returns the translation.
        
        Returns
        -------
        list of 3 floats
            The translation in the 3 directions [Tx,Ty,Tz].
            """
        return -self.tformMatrix[0:-1, -1]

    def initFromTranslationAndRotationVectors(self, transVec=[0, 0, 0], rotVec=[0, 0, 0]):
        """
        Initializes the transformation matrix from translation and rotation vectors.

        Parameters
        ----------
        transVec : list of 3 floats (default: [0,0,0])
            translation vector.
        rotVec : list of 3 floats (default: [0,0,0])
            rotation vector.
        """
        self.tformMatrix = transform3DMatrixFromTranslationAndRotationsVectors(transVec=transVec, rotVec=rotVec)


    def inverseTransform(self):

        self.tformMatrix = np.linalg.inv(self.tformMatrix)