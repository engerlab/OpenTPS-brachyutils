from abc import abstractmethod

import numpy as np
from scipy.sparse import csr_matrix

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.beamletDose import BeamletDose
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator


class CacheDoseCalculator:
    def __init__(self):
        self.beamModel = None
        self.ctCalibration = None
        self.ct = None
        self.plan = None
        self.nbPrimaries = 1e4
        self._doseCalculator = MCsquareDoseCalculator()

        self._weights:np.ndarray = None
        self._dose:DoseImage = None
        self._beamlets:BeamletDose = None

    @abstractmethod
    def computeDose(self, weights:np.ndarray) -> DoseImage:
        if not np.array_equal(weights, self._weights):
            self._weights = weights
            self._recomputeDose()

        return self._dose

    @abstractmethod
    def computeBeamlets(self) -> BeamletDose:
        if self._beamlets is None:
            self._recomputeBeamlets()

        return self._beamlets

    def _recomputeBeamlets(self):
        self._doseCalculator.beamModel = self.beamModel
        self._doseCalculator.ctCalibration = self.ctCalibration
        self._doseCalculator.nbPrimaries = self.nbPrimaries

        self._beamlets = self._doseCalculator.computeBeamlets(self.ct, self.plan)

    def _recomputeDose(self):
        if self._beamlets is None:
            self._recomputeBeamlets()

        self._beamlets.beamletWeights = self._weights
        self._dose = self._beamlets.toDoseImage()


class AbstractDoseFidelityTerm:
    @abstractmethod
    def getValue(self, weights:np.ndarray) -> float:
        raise NotImplementedError()

    @abstractmethod
    def getDerivative(self, weights:np.ndarray) -> np.ndarray:
        raise NotImplementedError()

class ObjectiveFunction(AbstractDoseFidelityTerm):
    def __init__(self):
        self._objectiveTerms = []
        self._termWeights = []

    def appendTerm(self, term:AbstractDoseFidelityTerm, weight:float):
        self._objectiveTerms.append(term)
        self._termWeights.append(weight)


class DoseMaxObjective(AbstractDoseFidelityTerm):
    def __init__(self, roi:ROIMask, maxDose:float, doseCalculator:CacheDoseCalculator):
        self.roi:ROIMask = roi
        self.maxDose:float = maxDose
        self.doseCalculator:CacheDoseCalculator = doseCalculator

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray)

    def getValue(self, weights:np.ndarray) -> float:
        doseImage = self.doseCalculator.computeDose(weights)

        dose = doseImage.imageArray
        # dose = dose[self.roi.imageArray.astype(bool)]
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.
        dose = dose.flatten()

        val = np.maximum(0., dose-self.maxDose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getDerivative(self, weights:np.ndarray) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights)

        dose = doseImage.imageArray
        # dose = dose[self.roi.imageArray.astype(bool)]
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.
        dose = dose.flatten()

        diff = np.maximum(0., dose - self.maxDose)
        diff = csr_matrix(diff) @ self.doseCalculator.computeBeamlets().toSparseMatrix()  # Would csc-ssc matrix multiplication be more efficient?
        diff *= 2 / self._roiVoxels

        diff = diff.toarray()

        return diff


class DoseMinObjective(AbstractDoseFidelityTerm):
    def __init__(self, roi:ROIMask, minDose:float, doseCalculator:CacheDoseCalculator):
        self.roi:ROIMask = roi
        self.minDose:float = minDose
        self.doseCalculator:CacheDoseCalculator = doseCalculator

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray)

    def getValue(self, weights:np.ndarray) -> float:
        doseImage = self.doseCalculator.computeDose(weights)

        dose = doseImage.imageArray
        # dose = dose[self.roi.imageArray.astype(bool)]
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.
        dose = dose.flatten()

        val = np.maximum(0., self.minDose-dose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getDerivative(self, weights:np.ndarray) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights)

        dose = doseImage.imageArray
        #dose = dose[self.roi.imageArray.astype(bool)]
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.
        dose = dose.flatten()

        diff = np.maximum(0., self.minDose-dose)
        diff = np.transpose(diff)
        diff = csr_matrix(diff) @ self.doseCalculator.computeBeamlets().toSparseMatrix() # Would csc-ssc matrix multiplication be more efficient?
        diff *= -2 / self._roiVoxels

        diff = diff.toarray()

        return diff
