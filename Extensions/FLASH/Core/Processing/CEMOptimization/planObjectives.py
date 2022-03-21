
from abc import abstractmethod

import numpy as np

from Core.Data.Images.roiMask import ROIMask


class AbstractDoseFidelityTerm:
    @abstractmethod
    def getValue(self, weights:np.ndarray) -> float:
        raise NotImplementedError()

    @abstractmethod
    def getDerivative(self, weights:np.ndarray) -> np.ndarray:
        raise NotImplementedError()


class DoseMaxObjective(AbstractDoseFidelityTerm):
    def __init__(self, roi:ROIMask, maxDose:float, doseCalculator):
        self.roi:ROIMask = roi
        self.maxDose:float = maxDose
        self.doseCalculator = doseCalculator

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray.astype(int))

    def getValue(self, weights:np.ndarray) -> float:
        doseImage = self.doseCalculator.computeDose(weights)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.

        dose = dose.flatten()

        val = np.maximum(0., dose-self.maxDose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getDerivative(self, weights:np.ndarray) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.

        dose = np.flip(dose, 0)
        dose = np.flip(dose, 1)
        dose = dose.flatten(order='F')

        diff = np.maximum(0., dose - self.maxDose)
        diff = np.transpose(diff)

        diff = diff @ self.doseCalculator.computeBeamlets().toSparseMatrix()
        diff *= 2. / self._roiVoxels

        diff *= self.doseCalculator.computeBeamlets().beamletRescaling

        return diff


class DoseMinObjective(AbstractDoseFidelityTerm):
    def __init__(self, roi:ROIMask, minDose:float, doseCalculator):
        self.roi:ROIMask = roi
        self.minDose:float = minDose
        self.doseCalculator = doseCalculator

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray)

    def getValue(self, weights:np.ndarray) -> float:
        doseImage = self.doseCalculator.computeDose(weights)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = self.minDose
        dose = dose.flatten()

        val = np.maximum(0., self.minDose-dose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getDerivative(self, weights:np.ndarray) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = self.minDose

        dose = np.flip(dose, 0)
        dose = np.flip(dose, 1)
        dose = dose.flatten(order='F')

        diff = np.maximum(0., self.minDose-dose)
        diff = np.transpose(diff)

        diff = diff @ self.doseCalculator.computeBeamlets().toSparseMatrix()
        diff *= -2. / self._roiVoxels

        diff *= self.doseCalculator.computeBeamlets().beamletRescaling

        return diff
