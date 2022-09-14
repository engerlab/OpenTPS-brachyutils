__all__ = ['SparseBeamlets']

import logging
import pickle
from typing import Sequence, Optional

import numpy as np
import scipy.sparse as sp
from scipy.sparse import csc_matrix

try:
    import sparse_dot_mkl

    use_MKL = 1
except:
    use_MKL = 0

from Core.Data.Images._doseImage import DoseImage
from Core.Data.Images._image3D import Image3D
from Core.Data._patientData import PatientData

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

        self._savedBeamletFile = ""

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
        weights = np.array(self._weights)

        totalDose = csc_matrix.dot(self._sparseBeamlets, weights)

        totalDose = np.reshape(totalDose, self._gridSize, order='F')
        totalDose = np.flip(totalDose, 0)
        totalDose = np.flip(totalDose, 1)

        doseImage = DoseImage(imageArray=totalDose, origin=self._origin, spacing=self._spacing,
                              angles=self._orientation)
        doseImage.patient = self.patient

        return doseImage

    def toSparseMatrix(self) -> csc_matrix:
        return self._sparseBeamlets

    def cropFromROI(self, plan):
        roiObjectives = np.zeros(plan.planDesign.ct.numberOfVoxels).astype(bool)
        roiRobustObjectives = np.zeros(plan.planDesign.ct.numberOfVoxels).astype(bool)
        robust = False
        for objective in plan.planDesign.objectives.fidObjList:
            if objective.robust:
                robust = True
                roiRobustObjectives = np.logical_or(roiRobustObjectives, objective.maskVec)
            else:
                roiObjectives = np.logical_or(roiObjectives, objective.maskVec)
        roiObjectives = np.logical_or(roiObjectives, roiRobustObjectives)

        # reload beamlets and crop to optimization ROI
        logger.info("Crop beamlets to optimization ROI...")
        if use_MKL == 1:
            beamletMatrix = sparse_dot_mkl.dot_product_mkl(
                sp.diags(roiObjectives.astype(np.float32), format='csc'), self.toSparseMatrix())
        else:
            beamletMatrix = sp.csc_matrix.dot(sp.diags(roiObjectives.astype(np.float32), format='csc'),
                                              self.toSparseMatrix())

        if robust:
            for s in range(len(plan.planDesign.scenarios)):
                plan.planDesign.scenarios[s].load()
                if use_MKL == 1:
                    plan.planDesign.scenarios[s].BeamletMatrix = sparse_dot_mkl.dot_product_mkl(
                        sp.diags(roiRobustObjectives.astype(np.float32), format='csc'),
                        plan.planDesign.scenarios[s].BeamletMatrix)
                else:
                    plan.scenarios[s].BeamletMatrix = sp.csc_matrix.dot(
                        sp.diags(roiRobustObjectives.astype(np.float32), format='csc'),
                        plan.planDesign.scenarios[s].BeamletMatrix)
        self.setUnitaryBeamlets(beamletMatrix)

    def load(self, file_path=""):
        if file_path == "":
            file_path = self._savedBeamletFile

        with open(file_path, 'rb') as fid:
            tmp = pickle.load(fid)

        self.__dict__.update(tmp)

    def unload(self):
        self._sparseBeamlets = []
