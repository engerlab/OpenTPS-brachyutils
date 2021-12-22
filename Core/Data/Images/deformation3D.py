import logging

from Core.Data.Images.image3D import Image3D
from Core.Data.Images.vectorField3D import VectorField3D

logger = logging.getLogger(__name__)


class Deformation3D(Image3D):

    def __init__(self, data=None, name="Deformation", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), UID=""):

        super().__init__(data=data, name=name, patientInfo=patientInfo, origin=origin, spacing=spacing, angles=angles, UID=UID)

        self.velocity = None
        self.displacement = None

    def getGridSize(self):
        if (self.velocity is None) and (self.displacement is None):
            return (0, 0, 0)
        elif self.displacement is None:
            return self.velocity.data.shape[0:3]
        else:
            return self.displacement.data.shape[0:3]

    def initFromImage(self, image):
        self.velocity = VectorField3D()
        self.velocity.initFromImage(image)
        self.displacement = None
        self.origin = image.origin
        self.spacing = image.spacing
        self.angles = image.angles
        self.patientInfo = image.patientInfo

    def initFromVelocityField(self, field):
        self.velocity = field
        self.displacement = None
        self.origin = field.origin
        self.spacing = field.spacing
        self.angles = field.angles
        self.patientInfo = field.patientInfo

    def initFromDisplacementField(self, field):
        self.velocity = None
        self.displacement = field
        self.origin = field.origin
        self.spacing = field.spacing
        self.angles = field.angles
        self.patientInfo = field.patientInfo

    def resample(self, gridSize, origin, spacing, fillValue=0, outputType=None):
        if not(self.velocity is None):
            self.velocity.resample(gridSize, origin, spacing, fillValue=fillValue, outputType=outputType)
        if not(self.displacement is None):
            self.displacement.resample(gridSize, origin, spacing, fillValue=fillValue, outputType=outputType)
        self.origin = list(origin)
        self.spacing = list(spacing)

    def deformImage(self, image, fillValue=-1000):

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
