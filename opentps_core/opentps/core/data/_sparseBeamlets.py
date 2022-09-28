__all__ = ['SparseBeamlets']

import logging
import pickle
from typing import Sequence, Optional

import numpy as np
from opentps.core.io.serializedObjectIO import saveData
from scipy.sparse import csc_matrix

try:
    import sparse_dot_mkl

    use_MKL = 1
except:
    use_MKL = 0

from opentps.core.data.images._doseImage import DoseImage
from opentps.core.data.images._image3D import Image3D
from opentps.core.data._patientData import PatientData

logger = logging.getLogger(__name__)


class SparseBeamlets(PatientData):
    def __init__(self):
        super().__init__()

        self._sparseBeamlets = None
        self._weights = None
        self._origin = (0, 0, 0)
        self._spacing = (1, 1, 1)
        self._gridSize = (0, 0, 0)
        self._orientation = (1, 0, 0, 0, 1, 0, 0, 0, 1)

        self._savedBeamletFile = None

    @property
    def beamletWeights(self) -> Optional[Sequence]:
        return self._weights

    @beamletWeights.setter
    def beamletWeights(self, weights: Sequence):
        self._weights = weights

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
        weights = np.array(self._weights, dtype=np.float32)
        if use_MKL == 1:
            totalDose = sparse_dot_mkl.dot_product_mkl(self._sparseBeamlets, weights)
        else:
            totalDose = csc_matrix.dot(self._sparseBeamlets, weights)

        totalDose = np.reshape(totalDose, self._gridSize, order='F')
        totalDose = np.flip(totalDose, 0)
        totalDose = np.flip(totalDose, 1)

        doseImage = DoseImage(imageArray=totalDose, origin=self._origin, spacing=self._spacing,
                              angles=self._orientation)
        doseImage.patient = self.patient

        return doseImage

    def toSparseMatrix(self) -> csc_matrix:
        if self._sparseBeamlets is None and not(self._savedBeamletFile is None):
            self.reloadFromFS()
        return self._sparseBeamlets

    def reloadFromFS(self):
        with open(self._savedBeamletFile, 'rb') as fid:
            tmp = pickle.load(fid)
        self.__dict__.update(tmp)

    def storeOnFS(self, filePath):
        self._savedBeamletFile = filePath
        saveData(self, self._savedBeamletFile)
        self.unload()

    def unload(self):
        self._sparseBeamlets = None
