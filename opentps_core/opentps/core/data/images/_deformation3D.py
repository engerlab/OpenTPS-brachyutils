
__all__ = ['Deformation3D']


import logging
import numpy as np
import copy
from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images._vectorField3D import VectorField3D

logger = logging.getLogger(__name__)


class Deformation3D(Image3D):
    """
    Class for 3D deformations (velocity and/or displacement fields). Inherits from Image3D and its attributes.

    Attributes
    ----------
    velocity : VectorField3D
        Velocity field of the deformation.
    displacement : VectorField3D
        Displacement field of the deformation.

    Raises
    ------
    Error if both velocity and displacement are initialized but have different origin or spacing.
    """

    def __init__(self, imageArray=None, name="Deformation", origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), seriesInstanceUID="", velocity=None, displacement=None, patient=None):

        if (displacement is None) and not(velocity is None):
            origin = velocity._origin
            spacing = velocity._spacing
        elif (velocity is None) and not(displacement is None):
            origin = displacement._origin
            spacing = displacement._spacing
        elif not(velocity is None) and not(displacement is None):
            if np.array_equal(velocity._origin, displacement._origin):
                origin = velocity._origin
            else:
                logger.error("Velocity and displacement fields have different origin. Cannot create deformation object.")
            if np.array_equal(velocity._spacing, displacement._spacing):
                spacing = velocity._spacing
            else:
                logger.error("Velocity and displacement fields have different spacing. Cannot create deformation object.")

        self.velocity = velocity
        self.displacement = displacement

        super().__init__(imageArray=imageArray, name=name, origin=origin, spacing=spacing, angles=angles, seriesInstanceUID=seriesInstanceUID, patient=patient)

    @property
    def gridSize(self):
        """
        Compute the voxel grid size of the deformation.

        Returns
        -------
        np.array
            Grid size of velocity field and/or displacement field.
        """

        if (self.velocity is None) and (self.displacement is None):
            return np.array([0, 0, 0])
        elif self.displacement is None:
            return np.array([self.velocity.imageArray.shape[0:3]])[0]
        else:
            return np.array([self.displacement._imageArray.shape[0:3]])[0]

    def copy(self):
        """
        Create a copy of the deformation.

        Returns
        -------
        Deformation3D
            Copy of the deformation.
        """
        return Deformation3D(velocity=copy.deepcopy(self.velocity), displacement=copy.deepcopy(self.displacement), name=self.name + '_copy', origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID)

    def setVelocity(self, velocity):
        """
        Set velocity field of the deformation. Displacement field is set to None.

        Parameters
        ----------
        velocity : VectorField3D
            Velocity field of the deformation.
        """
        self.velocity = velocity
        self.displacement = None

    def setDisplacement(self, displacement):
        """
        Set displacement field of the deformation. Velocity field is set to None.

        Parameters
        ----------
        displacement : VectorField3D
            Displacement field of the deformation.
        """
        self.displacement = displacement
        self.velocity = None

    def setVelocityArray(self, velocityArray):
        """
        Set the image array of the velocity field of the deformation. Displacement field is set to None.

        Parameters
        ----------
        velocityArray : numpy array
            Image array of the velocity field of the deformation.
        """
        self.velocity._imageArray = velocityArray
        self.displacement = None

    def setDisplacementArray(self, displacementArray):
        """
        Set the image array of the displacement field of the deformation. Velocity field is set to None.

        Parameters
        ----------
        displacementArray : numpy array
            Image array of the displacement field of the deformation.
        """
        self.displacement._imageArray = displacementArray
        self.velocity = None

    def setVelocityArrayXYZ(self, velocityArrayX, velocityArrayY, velocityArrayZ):
        """
        Set the image array of the velocity field of the deformation. Displacement field is set to None.

        Parameters
        ----------
        velocityArrayX : numpy array
            Image array of the velocity field of the deformation in x direction.
        velocityArrayY : numpy array
            Image array of the velocity field of the deformation in y direction.
        velocityArrayZ : numpy array
            Image array of the velocity field of the deformation in z direction.
        """
        self.velocity._imageArray[:, :, :, 0] = velocityArrayX
        self.velocity._imageArray[:, :, :, 1] = velocityArrayY
        self.velocity._imageArray[:, :, :, 2] = velocityArrayZ
        self.displacement = None

    def setDisplacementArrayXYZ(self, displacementArrayX, displacementArrayY, displacementArrayZ):
        """
        Set the image array of the displacement field of the deformation. Velocity field is set to None.

        Parameters
        ----------
        displacementArrayX : numpy array
            Image array of the displacement field of the deformation in x direction.
        displacementArrayY : numpy array
            Image array of the displacement field of the deformation in y direction.
        displacementArrayZ : numpy array
            Image array of the displacement field of the deformation in z direction.
        """
        self.displacement._imageArray[:, :, :, 0] = displacementArrayX
        self.displacement._imageArray[:, :, :, 1] = displacementArrayY
        self.displacement._imageArray[:, :, :, 2] = displacementArrayZ
        self.velocity = None

    def initFromImage(self, image):
        """
        Initialize deformation using the voxel grid of the input image.

        Parameters
        ----------
        image : numpy array
            image from which the voxel grid is copied.
        """

        self.velocity = VectorField3D()
        self.velocity.initFromImage(image)
        self.displacement = None
        self.origin = image._origin
        self.spacing = image._spacing
        self.angles = image._angles

    def initFromVelocityField(self, field):
        """
        Initialize deformation using the input field as velocity.

        Parameters
        ----------
        field : numpy array
            field used as velocity in the deformation.
        """

        self.velocity = field.copy()
        self.displacement = None
        self.origin = field._origin
        self.spacing = field._spacing
        self.angles = field._angles

    def initFromDisplacementField(self, field):
        """
        Initialize deformation using the input field as displacement.

        Parameters
        ----------
        field : numpy array
            field used as displacement in the deformation.
        """

        self.velocity = None
        self.displacement = field.copy()
        self.origin = field._origin
        self.spacing = field._spacing
        self.angles = field._angles

    def resample(self, spacing, gridSize, origin, fillValue=0, outputType=None, tryGPU=True):
        """
        Resample deformation (velocity and/or displacement field) according to new voxel grid using linear interpolation.

        Parameters
        ----------
        gridSize : list
            size of the resampled deformation voxel grid.
        origin : list
            origin of the resampled deformation voxel grid.
        spacing : list
            spacing of the resampled deformation voxel grid.
        fillValue : scalar
            interpolation value for locations outside the input voxel grid.
        outputType : numpy data type
            type of the output.
        """

        from opentps.core.processing.imageProcessing.resampler3D import resample
        resample(self, spacing=spacing, gridSize=gridSize, origin=origin, fillValue=fillValue, tryGPU=tryGPU, outputType=outputType, inPlace=True)

        # if not(self.velocity is None):
        #     self.velocity.resample(spacing, gridSize, origin, fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)
        # if not(self.displacement is None):
        #     self.displacement.resample(spacing, gridSize, origin, fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)
        # self.origin = np.array(origin)
        # self.spacing = np.array(spacing)

    def deformImage(self, image, fillValue='closest', outputType=np.float32, tryGPU=True):
        """
        Deform 3D image using linear interpolation.

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
    
        if (self.displacement is None):
            self.displacement = self.velocity.exponentiateField(tryGPU=tryGPU)
        
        field = self.displacement.copy()

        if tuple(self.gridSize) != tuple(image.gridSize) or tuple(self.origin) != tuple(image._origin) or tuple(self.spacing) != tuple(image._spacing):
            logger.info("Image and field dimensions do not match. Resample displacement field to image grid before deformation.")
            # print('in deformation3D deformImage before resample', image.gridSize, field.gridSize)
            field.resample(image.spacing, image.gridSize, image.origin, tryGPU=tryGPU)
            # print('in deformation3D deformImage after resample', image.gridSize, field.gridSize)
        
        image = image.copy()
        init_dtype = image.imageArray.dtype

        if isinstance(image, VectorField3D):
            image.imageArray[:, :, :, 0] = field.warp(image.imageArray[:, :, :, 0], fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)
            image.imageArray[:, :, :, 1] = field.warp(image.imageArray[:, :, :, 1], fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)
            image.imageArray[:, :, :, 2] = field.warp(image.imageArray[:, :, :, 2], fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)
            
        else:
            image.imageArray = field.warp(image.imageArray, fillValue=fillValue, outputType=outputType, tryGPU=tryGPU)


        if init_dtype == 'bool':
            
            testArray = image.imageArray
            testArray[testArray < 0.5] = 0
            testArray[testArray >= 0.5] = 1
            # image._imageArray[image._imageArray < 0.5] = 0
            # image._imageArray[image._imageArray >= 0.5] = 1
            image.imageArray = testArray.astype(bool)

        return image

    def createDisplacementFromVelocity(self, tryGPU=True):
        if self.velocity is None:
            logger.error("Velocity field is None, creating displacement field from velocity field is impossible.")
        else:
            self.displacement = self.velocity.exponentiateField(tryGPU=tryGPU)


    def inverse(self):
        if self.velocity is None:
            logger.error("Inversing a Deformation3D without the velocity field is not possible for now.")
        else:
            if self.displacement is not None:
                self.displacement = None

            self.velocity.imageArray = -self.velocity.imageArray

    def dumpableCopy(self):
        """
        Create a copy of the deformation that can be dumped to disk.

        Returns
        -------
        Deformation3D
            Copy of the deformation that can be dumped to disk.
        """
        dumpableDef = Deformation3D(imageArray=self.imageArray, name=self.name, origin=self.origin, spacing=self.spacing, angles=self.angles, seriesInstanceUID=self.seriesInstanceUID, velocity=self.velocity, displacement=self.displacement)
        # dumpableDef.patient = self.patient
        return dumpableDef
