import pydicom
import numpy as np
import scipy.ndimage
import math
import logging

from Core.Data.Images.image3D import Image3D
from Core.Data.Images.vectorField3D import VectorField3D

logger = logging.getLogger(__name__)


class Deformation3D(Image3D):

    def __init__(self, data=None, name="3D Deformation", patientInfo=None, origin=(0, 0, 0), spacing=(1, 1, 1), angles=(0, 0, 0), UID=""):

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
        self.origin = image.origin
        self.spacing = image.spacing

    def import_Dicom_DF(self, DcmFile, df_type='Velocity'):

        dcm = pydicom.dcmread(DcmFile).DeformableRegistrationSequence[0]

        # import deformation field
        dcm_field = dcm.DeformableRegistrationGridSequence[0]

        self.origin = dcm_field.ImagePositionPatient
        self.spacing = dcm_field.GridResolution

        raw_field = np.frombuffer(dcm_field.VectorGridData, dtype=np.float32)
        raw_field = raw_field.reshape(
            (3, dcm_field.GridDimensions[0], dcm_field.GridDimensions[1], dcm_field.GridDimensions[2]),
            order='F').transpose(1, 2, 3, 0)
        field = raw_field.copy()
        for i in range(3):
            field[:, :, :, i] = field[:, :, :, i] / self.spacing[i]

        if df_type == 'Velocity':
            self.velocity = VectorField3D()
            self.velocity.data = field
            self.velocity.origin = self.origin
            self.velocity.spacing = self.spacing
        elif df_type == 'Displacement':
            self.displacement = VectorField3D()
            self.displacement.data = field
            self.displacement.origin = self.origin
            self.displacement.spacing = self.spacing
        else:
            logger.error("Unknown deformation field type")
            return

    def resample(self, gridSize, origin, spacing, fillValue=0):
        if not(self.velocity is None):
            self.velocity.resample(gridSize, origin, spacing, fillValue=fillValue)
        if not(self.displacement is None):
            self.displacement.resample(gridSize, origin, spacing, fillValue=fillValue)
        self.origin = list(origin)
        self.spacing = list(spacing)

    def deformImage(self, Image, fillValue=-1000):

        if (self.displacement is None):
            field = self.velocity.exponentiateField()
        else:
            field = self.displacement

        if tuple(self.getGridSize()) != tuple(Image.getGridSize()) or tuple(self.origin) != tuple(
                Image.origin) or tuple(self.spacing) != tuple(Image.spacing):
            field = self.resampleVectorField(field, Image.getGridSize(), Image.origin, Image.spacing)
            logger.warning("Image and field dimensions do not match. Resample displacement field to image grid.")

        Image.data = field.warp(Image.data, fillValue=fillValue)

