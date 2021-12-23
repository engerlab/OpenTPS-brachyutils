import logging

from Core.Data.Images.image3D import Image3D
from Core.Data.Images.vectorField3D import VectorField3D

logger = logging.getLogger(__name__)


class Deformation3D(Image3D):

    def __init__(self, data=None, name="Deformation", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), UID="", velocity=None, displacement=None):

        if (displacement is None) and not(velocity is None):
            origin = velocity.origin
            spacing = velocity.spacing
            if patientInfo is None:
                patientInfo = velocity.patientInfo
        elif (velocity is None) and not(displacement is None):
            origin = displacement.origin
            spacing = displacement.spacing
            if patientInfo is None:
                patientInfo = displacement.patientInfo
        elif not(velocity is None) and not(displacement is None):
            if velocity.origin == displacement.origin:
                origin = velocity.origin
            else:
                logger.error("Velocity and displacement fields have different origin. Cannot create deformation object.")
            if velocity.spacing == displacement.spacing:
                spacing = velocity.spacing
            else:
                logger.error("Velocity and displacement fields have different spacing. Cannot create deformation object.")
            if patientInfo is None:
                patientInfo = displacement.patientInfo

        super().__init__(data=data, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing, angles=angles, UID=UID)

        self.velocity = velocity
        self.displacement = displacement

    def getGridSize(self):
        """Compute the voxel grid size of the deformation.

            Returns
            -------
            list
                Grid size of velocity field and/or displacement field.
            """

        if (self.velocity is None) and (self.displacement is None):
            return (0, 0, 0)
        elif self.displacement is None:
            return self.velocity.data.shape[0:3]
        else:
            return self.displacement.data.shape[0:3]

    def initFromImage(self, image):
        """Initialize deformation using the voxel grid of the input image.

            Parameters
            ----------
            image : numpy array
                image from which the voxel grid is copied.
            """

        self.velocity = VectorField3D()
        self.velocity.initFromImage(image)
        self.displacement = None
        self.origin = image.origin
        self.spacing = image.spacing
        self.angles = image.angles
        self.patientInfo = image.patientInfo

    def initFromVelocityField(self, field):
        """Initialize deformation using the input field as velocity.

            Parameters
            ----------
            field : numpy array
                field used as velocity in the deformation.
            """

        self.velocity = field
        self.displacement = None
        self.origin = field.origin
        self.spacing = field.spacing
        self.angles = field.angles
        self.patientInfo = field.patientInfo

    def initFromDisplacementField(self, field):
        """Initialize deformation using the input field as displacement.

            Parameters
            ----------
            field : numpy array
                field used as displacement in the deformation.
            """

        self.velocity = None
        self.displacement = field
        self.origin = field.origin
        self.spacing = field.spacing
        self.angles = field.angles
        self.patientInfo = field.patientInfo

    def resample(self, gridSize, origin, spacing, fillValue=0, outputType=None):
        """Resample deformation (velocity and/or displacement field) according to new voxel grid using linear interpolation.

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

        if not(self.velocity is None):
            self.velocity.resample(gridSize, origin, spacing, fillValue=fillValue, outputType=outputType)
        if not(self.displacement is None):
            self.displacement.resample(gridSize, origin, spacing, fillValue=fillValue, outputType=outputType)
        self.origin = list(origin)
        self.spacing = list(spacing)

    def deformImage(self, image, fillValue=-1000):
        """Deform 3D image using linear interpolation.

            Parameters
            ----------
            image : numpy array
                image to be deformed.
            fillValue : scalar
                interpolation value for locations outside the input voxel grid.

            Returns
            -------
            numpy array
                Deformed image.
            """

        if (self.displacement is None):
            field = self.velocity.exponentiateField()
        else:
            field = self.displacement

        if tuple(self.getGridSize()) != tuple(image.getGridSize()) or tuple(self.origin) != tuple(
                image.origin) or tuple(self.spacing) != tuple(image.spacing):
            logger.warning("Image and field dimensions do not match. Resample displacement field to image grid.")
            field = field.copy()
            field.resample(image.getGridSize(), image.origin, image.spacing)

        image = image.copy()
        image.data = field.warp(image.data, fillValue=fillValue)

        return image
