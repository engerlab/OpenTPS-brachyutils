from abc import abstractmethod
from typing import Sequence, Union

import numpy as np

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Processing.ImageProcessing.imageTransform3D import ImageTransform3D
from Extensions.FLASH.Core.Processing.CEMOptimization import planObjectives
from Extensions.FLASH.Core.Processing.DoseCalculation.fluenceBasedMCsquareDoseCalculator import Beamlets


class CEMAbstractDoseFidelityTerm:
    def __init__(self):
        self._weightObjective = None
        self.beamModel = None

        self._roi = None
        self._doseCalculator = None

    @property
    def roi(self) -> ROIMask:
        return self._roi

    @roi.setter
    def roi(self, roiMask:ROIMask):
        self._roi = roiMask
        self._weightObjective.roi = self._roi

    @property
    def doseCalculator(self):
        return self._doseCalculator

    @doseCalculator.setter
    def doseCalculator(self, dc):
        self._doseCalculator = dc
        self._weightObjective.roi = self._doseCalculator

    @abstractmethod
    def getValue(self, weights: np.ndarray, cemThickness: np.ndarray) -> float:
        raise NotImplementedError()

    @abstractmethod
    def getCEMDerivative(self, weights:np.ndarray, cemVals:np.ndarray) -> np.ndarray:
        raise NotImplementedError()

    def getWeightDerivative(self, weights:np.ndarray, cemVals:np.ndarray) -> np.ndarray:
        return self._weightObjective.getDerivative(weights)

    def _multiplyWithDerivative(self, vec:np.ndarray, derivative:Union[Beamlets, Sequence[DoseImage]]) -> np.ndarray:
        if isinstance(derivative, Beamlets):
            return self._multiplyWithDerivative_Beamlets(vec, derivative)
        elif isinstance(derivative, Sequence):
            return self._multiplyWithDerivative_Sequence(vec, derivative)
        else:
            raise ValueError('Derivative cannot be of type ' + str(type(derivative)))

    def _multiplyWithDerivative_Beamlets(self, vec:np.ndarray, derivative:Beamlets) -> np.ndarray:
        derivativeMat = derivative.sparseBeamlets.toSparseMatrix()
        derivativePlan = derivative.referencePlan
        originalPlan = self.doseCalculator.plan

        productRes = vec @ derivativeMat
        res = np.array([])

        productInd = 0
        for b, beam in enumerate(derivativePlan):
            beamSubproduct = np.zeros(originalPlan[b].cem.imageArray.shape)

            ctBEV = ImageTransform3D.dicomToIECGantry(self.doseCalculator._ct, beam)
            isocenterBEV = ImageTransform3D.dicomCoordinate2iecGantry(self.doseCalculator._ct, beam, beam.isocenterPosition)

            for layer in beam:
                pos0Nozzle = np.array(layer.spotX) * (self.beamModel.smx - self.beamModel.nozzle_isocenter) / self.beamModel.smx
                pos1Nozzle = np.array(layer.spotY) * (self.beamModel.smx - self.beamModel.nozzle_isocenter) / self.beamModel.smy

                pos0Nozzle += isocenterBEV[0]
                pos1Nozzle = isocenterBEV[1] - pos1Nozzle

                for i, pos0 in enumerate(pos0Nozzle):
                    pos1 = pos1Nozzle[i]

                    vIndex = ctBEV.getVoxelIndexFromPosition([pos0, pos1, 0])
                    beamSubproduct[vIndex[0], vIndex[1]] = productRes[productInd]
                    productInd += 1

            res = np.concatenate((res, beamSubproduct.flatten()))

        return res

    def _multiplyWithDerivative_Sequence(self, vec:np.ndarray, derivativeSequence:Sequence[DoseImage]) -> np.ndarray:
        res = np.array([])

        for derivative in derivativeSequence:
            derivativeMat = derivative.imageArray

            derivativeMat = np.flip(derivativeMat, 0)
            derivativeMat = np.flip(derivativeMat, 1)
            derivativeMat = derivativeMat.flatten(order='F')

            if len(res)==0:
                res = np.array(vec@derivativeMat)
            else:
                res = np.concatenate((res, vec@derivativeMat))

        return res


class DoseMaxObjective(CEMAbstractDoseFidelityTerm):
    def __init__(self, roi:ROIMask, maxDose:float, doseCalculator):
        super().__init__()
        self._weightObjective = planObjectives.DoseMaxObjective(roi, maxDose, doseCalculator)

        self._maxDose:float = maxDose
        self.roi = roi
        self.doseCalculator = doseCalculator

    @property
    def maxDose(self):
        return self._maxDose

    @maxDose.setter
    def maxDose(self, dose):
        self._maxDose = dose
        self._weightObjective.maxDose = dose

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray.astype(int))

    def getValue(self, weights:np.ndarray, cemThickness: np.ndarray) -> float:
        doseImage = self.doseCalculator.computeDose(weights, cemThickness)

        dose = doseImage.imageArray
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.

        dose = dose.flatten()

        val = np.maximum(0., dose-self.maxDose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getCEMDerivative(self, weights:np.ndarray, cemVals:np.ndarray) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights, cemVals)

        dose = doseImage.imageArray
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.

        dose = np.flip(dose, 0)
        dose = np.flip(dose, 1)
        dose = dose.flatten(order='F')

        diff = np.maximum(0., dose - self.maxDose)
        diff = np.transpose(diff)

        diff = self._multiplyWithDerivative(diff, self.doseCalculator.computeDerivative(weights, cemVals))
        diff *= 2. / self._roiVoxels

        return diff

    def getWeightDerivative(self, weights:np.ndarray, cemVals:np.ndarray) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights, cemVals)

        dose = doseImage.imageArray
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.

        dose = np.flip(dose, 0)
        dose = np.flip(dose, 1)
        dose = dose.flatten(order='F')

        diff = np.maximum(0., dose - self.maxDose)
        diff = np.transpose(diff)

        diff = diff @ self.doseCalculator.computeBeamlets(cemVals).toSparseMatrix()
        diff *= 2. / self._roiVoxels

        diff *= self.doseCalculator.computeBeamlets(cemVals).beamletRescaling

        return diff


class DoseMinObjective(CEMAbstractDoseFidelityTerm):
    def __init__(self, roi:ROIMask, minDose:float, doseCalculator):
        super().__init__()

        self._weightObjective = planObjectives.DoseMinObjective(roi, minDose, doseCalculator)

        self._minDose: float = minDose
        self.roi = roi
        self.doseCalculator = doseCalculator

    @property
    def minDose(self):
        return self._minDose

    @minDose.setter
    def minDose(self, dose):
        self._minDose = dose
        self._weightObjective.minDose = dose

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray)

    def getValue(self, weights:np.ndarray, cemThickness:np.ndarray) -> float:
        doseImage = self.doseCalculator.computeDose(weights, cemThickness)

        dose = doseImage.imageArray
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = self.minDose
        dose = dose.flatten()

        val = np.maximum(0., self.minDose-dose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getCEMDerivative(self, weights:np.ndarray, cemVals:np.ndarray) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights, cemVals)

        dose = doseImage.imageArray
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = self.minDose

        dose = np.flip(dose, 0)
        dose = np.flip(dose, 1)
        dose = dose.flatten(order='F')

        diff = np.maximum(0., self.minDose-dose)
        diff = np.transpose(diff)

        diff = self._multiplyWithDerivative(diff, self.doseCalculator.computeDerivative(weights, cemVals))
        diff *= -2. / self._roiVoxels

        return diff

    def getWeightDerivative(self, weights:np.ndarray, cemVals:np.ndarray) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights, cemVals)

        dose = doseImage.imageArray
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.

        dose = np.flip(dose, 0)
        dose = np.flip(dose, 1)
        dose = dose.flatten(order='F')

        diff = np.maximum(0., self.minDose-dose)
        diff = np.transpose(diff)

        diff = diff @ self.doseCalculator.computeBeamlets(cemVals).toSparseMatrix()
        diff *= -2. / self._roiVoxels

        diff *= self.doseCalculator.computeBeamlets(cemVals).beamletRescaling

        return diff
