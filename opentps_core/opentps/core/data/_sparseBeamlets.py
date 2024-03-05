__all__ = ['SparseBeamlets']

import logging
import pickle
from typing import Sequence, Optional

import numpy as np
from opentps.core.io.serializedObjectIO import saveData
from scipy.sparse import csc_matrix

from opentps.core.data.images._image3D import Image3D
from opentps.core.data._patientData import PatientData

logger = logging.getLogger(__name__)


class SparseBeamlets(PatientData):
    """
    Class for storing sparse beamlet data. Inherits from PatientData.

    Parameters
    ----------
    doseOrigin : tuple
        Origin of the dose grid
    doseSpacing : tuple
        Spacing of the dose grid
    doseGridSize : tuple
        Size of the dose grid
    doseOrientation : tuple
        Orientation of the dose grid
    shape : tuple
        Shape of the sparse beamlet matrix
    """
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
        """
        Sets the spatial referencing of the sparse beamlet matrix from an image

        Parameters
        ---------
        image : Image3D
            Image to use for spatial referencing
        """
        self.doseOrigin = image.origin
        self.doseSpacing = image.spacing
        self.doseOrientation = image.angles

    def setUnitaryBeamlets(self, beamlets: csc_matrix):
        """
        Sets the sparse beamlets matrix

        Parameters
        ---------
        beamlets : csc_matrix
            Sparse beamlets matrix
        """
        self._sparseBeamlets = beamlets

    def toSparseMatrix(self) -> csc_matrix:
        """
        Convert the sparse beamlets matrix (attribute) to a csc_matrix type

        Returns
        -------
        csc_matrix
            The sparse beamlets matrix
        """
        if self._sparseBeamlets is None and not(self._savedBeamletFile is None):
            self.reloadFromFS()
        return self._sparseBeamlets

    def reloadFromFS(self):
        """
        Reloads the sparse beamlets matrix from the file system
        """
        with open(self._savedBeamletFile, 'rb') as fid:
            tmp = pickle.load(fid)
        self.__dict__.update(tmp)

    def storeOnFS(self, filePath):
        """
        Stores the sparse beamlets matrix on the file system
        """
        self._savedBeamletFile = filePath
        saveData(self, self._savedBeamletFile)
        self.unload()

    def unload(self):
        """
        Unloads the sparse beamlets matrix from memory
        """
        self._sparseBeamlets = None
