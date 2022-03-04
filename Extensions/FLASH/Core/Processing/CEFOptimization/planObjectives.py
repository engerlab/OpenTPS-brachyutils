from abc import abstractmethod
from typing import Sequence

import numpy as np

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.beamletDose import BeamletDose


class AbstractDoseCalculator:
    @abstractmethod
    def getDose(self, weights) -> DoseImage:
        raise NotImplementedError()

    @abstractmethod
    def getBeamlets(self) -> BeamletDose:
        raise NotImplementedError()

class AbstractDoseFidelityTerm:
    @abstractmethod
    def getValue(self, weights:Sequence[float]) -> float:
        raise NotImplementedError()

    @abstractmethod
    def getDerivative(self, weights:Sequence[float]) -> Sequence[float]:
        raise NotImplementedError()

class ObjectiveFunction(AbstractDoseFidelityTerm):
    def __init__(self):
        self._objectiveTerms = []
        self._termWeights = []

    def appendTerm(self, term:AbstractDoseFidelityTerm, weight:float):
        self._objectiveTerms.append(term)
        self._termWeights.append(weight)

class DoseMaxObjective(AbstractDoseFidelityTerm):
    def __init__(self):
        self.roi:ROIMask = None
        self.maxDose:float = 0.
        self.doseCalculator:AbstractDoseCalculator = None

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray)

    def getValue(self, weights:Sequence[float]) -> float:
        doseImage = self.doseCalculator.getDose(weights)

        dose = doseImage.imageArray
        dose = dose[self.roi.imageArray.astype(bool)]
        dose = dose.flatten()

        val = np.maximum(0., dose-self.maxDose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getDerivative(self, weights:Sequence[float]) -> Sequence[float]:
        doseImage = self.doseCalculator.getDose(weights)

        dose = doseImage.imageArray
        dose = dose[self.roi.imageArray.astype(bool)]
        dose = dose.flatten()

        diff = np.maximum(0., dose - self.maxDose)
        diff *= 2 * self.doseCalculator.getBeamlets().toSparseMatrix()/ self._roiVoxels

        return diff

class DoseMinObjective(AbstractDoseFidelityTerm):
    def __init__(self):
        self.roi:ROIMask = None
        self.minDose:float = 0.
        self.doseCalculator:AbstractDoseCalculator = None

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray)

    def getValue(self, weights:Sequence[float]) -> float:
        doseImage = self.doseCalculator.getDose(weights)

        dose = doseImage.imageArray
        dose = dose[self.roi.imageArray.astype(bool)]
        dose = dose.flatten()

        val = np.maximum(0., self.minDose-dose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getDerivative(self, weights:Sequence[float]) -> Sequence[float]:
        doseImage = self.doseCalculator.getDose(weights)

        dose = doseImage.imageArray
        dose = dose[self.roi.imageArray.astype(bool)]
        dose = dose.flatten()

        diff = np.maximum(0., self.minDose-dose)
        diff *= -2 * self.doseCalculator.getBeamlets().toSparseMatrix()/ self._roiVoxels

        return diff
