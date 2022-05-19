from typing import Sequence, Optional

import numpy as np
from scipy.sparse import csc_matrix

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.image3D import Image3D
from Core.Data.patientData import PatientData


class SparseBeamlets(PatientData):
    def __init__(self):
        super().__init__()

        self._sparseBeamlets = None
        self._beamletRescaling = None
        self._weights = None
        self._origin = (0, 0, 0)
        self._spacing = (1, 1, 1)
        self._gridSize = (0, 0, 0)
        self._orientation = (1, 0, 0, 0, 1, 0, 0, 0, 1)

    @property
    def beamletWeights(self) -> Optional[Sequence]:
        return self._weights

    @beamletWeights.setter
    def beamletWeights(self, weights:Sequence):
        self._weights = weights

    @property
    def beamletRescaling(self) -> Optional[Sequence]:
        return self._beamletRescaling

    @beamletRescaling.setter
    def beamletRescaling(self, weights: Sequence):
        self._beamletRescaling = weights

    @property
    def doseOrigin(self):
        return self._origin

    @doseOrigin.setter
    def doseOrigin(self, origin):
        self._origin = origin

    @property
    def doseSpacing(self):
        return self._spacing

    @doseSpacing.setter
    def doseSpacing(self, spacing):
        self._spacing = spacing

    @property
    def doseGridSize(self):
        return self._gridSize

    @doseGridSize.setter
    def doseGridSize(self, size):
        self._gridSize = size

    @property
    def doseOrientation(self):
        return self._orientation

    @property
    def shape(self):
        return self._sparseBeamlets.shape

    @doseOrientation.setter
    def doseOrientation(self, orientation):
        self._orientation = orientation

    def setSpatialReferencingFromImage(self, image: Image3D):
        self.doseOrigin = image.origin
        self.doseSpacing = image.spacing
        self.doseOrientation = image.angles

    def setUnitaryBeamlets(self, beamlets: csc_matrix):
        self._sparseBeamlets = beamlets

    def toDoseImage(self) -> DoseImage:
        if not self._beamletRescaling is None:
            weights = np.array(self._beamletRescaling) * np.array(self._weights)
        else:
            weights = np.array(self._weights)

        totalDose = csc_matrix.dot(self._sparseBeamlets, weights)

        totalDose = np.reshape(totalDose, self._gridSize, order='F')
        totalDose = np.flip(totalDose, 0)
        totalDose = np.flip(totalDose, 1)

        doseImage =  DoseImage(imageArray=totalDose, origin=self._origin, spacing=self._spacing, angles=self._orientation)
        doseImage.patient = self.patient

        return doseImage

    def toSparseMatrix(self) -> csc_matrix:
        return self._sparseBeamlets

    def cropFromROI(self, roi):
        raise NotImplementedError()
