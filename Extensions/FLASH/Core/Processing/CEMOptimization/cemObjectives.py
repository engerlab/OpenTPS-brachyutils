import copy
from abc import abstractmethod
from typing import Sequence, Union

import numpy as np

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Extensions.FLASH.Core.Data.cem import BiComponentCEM
from Extensions.FLASH.Core.Processing.DoseCalculation.fluenceBasedMCsquareDoseCalculator import Beamlets


class CEMAbstractDoseFidelityTerm:
    def __init__(self):
        self._weightObjective = None
        self.beamModel = None # TODO: Should we take the beam model from the dose calculator to reduce the amount of parameters that must be set by the user

        self._roi = None
        self._doseCalculator = None

    def abort(self):
        self._doseCalculator.kill()

    @property
    def roi(self) -> ROIMask:
        return self._roi

    @roi.setter
    def roi(self, roiMask:ROIMask):
        self._roi = roiMask

    @property
    def doseCalculator(self):
        return self._doseCalculator

    @doseCalculator.setter
    def doseCalculator(self, dc):
        self._doseCalculator = dc

    @abstractmethod
    def getValue(self, weights: np.ndarray, cems:Sequence[BiComponentCEM]) -> float:
        raise NotImplementedError()

    @abstractmethod
    def getCEMDerivative(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> np.ndarray:
        raise NotImplementedError()

    @abstractmethod
    def getWeightDerivative(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> np.ndarray:
        raise NotImplementedError()

    def _multiplyWithDerivative(self, diff:DoseImage, derivative:Union[Beamlets, Sequence[DoseImage]], alpha:float=1.) -> Sequence[BiComponentCEM]:
        if isinstance(derivative, Beamlets):
            return self._multiplyWithDerivative_Beamlets(diff, derivative, alpha)
        elif isinstance(derivative, Sequence):
            return self._multiplyWithDerivative_Sequence(diff, derivative, alpha)
        else:
            raise ValueError('Derivative cannot be of type ' + str(type(derivative)))

    def _multiplyWithDerivative_Beamlets(self, diff:DoseImage, derivative:Beamlets, alpha:float=1.) -> Sequence[BiComponentCEM]:
        diffVal = diff.imageArray

        diffVal = np.flip(diffVal, 0)
        diffVal = np.flip(diffVal, 1)
        diffVal = diffVal.flatten(order='F')
        diffVal = np.transpose(diffVal)

        derivativeMat = derivative.sparseBeamlets.toSparseMatrix()
        derivativePlan = derivative.referencePlan
        originalPlan = self.doseCalculator.plan

        productRes = diffVal @ derivativeMat
        outCEMs = []

        productInd = 0
        for b, beam in enumerate(derivativePlan):
            beamSubproduct = np.zeros(originalPlan[b].cem.imageArray.shape)

            isocenterBEV = imageTransform3D.dicomCoordinate2iecGantry(diff, beam, beam.isocenterPosition)

            for layer in beam:
                pos0Nozzle = np.array(layer.spotX) * (self.beamModel.smx - self.beamModel.nozzle_isocenter) / self.beamModel.smx
                pos1Nozzle = np.array(layer.spotY) * (self.beamModel.smx - self.beamModel.nozzle_isocenter) / self.beamModel.smy

                pos0Nozzle += isocenterBEV[0]
                pos1Nozzle = isocenterBEV[1] - pos1Nozzle

                for i, pos0 in enumerate(pos0Nozzle):
                    pos1 = pos1Nozzle[i]

                    vIndex = originalPlan[b].cem.getVoxelIndexFromPosition([pos0, pos1])
                    try:
                        beamSubproduct[vIndex[0], vIndex[1]] = productRes[productInd]
                    except:
                        # Index outside CEM
                        pass
                    productInd += 1

            outCEM = copy.deepcopy(originalPlan[b].cem)
            outCEM.imageArray = beamSubproduct*alpha
            outCEMs.append(outCEM)

        return outCEMs

    def _multiplyWithDerivative_Sequence(self, diff:DoseImage, derivativeSequence:Sequence[DoseImage], alpha:float=1.) -> Sequence[BiComponentCEM]:
        outCEMs = []

        plan = self.doseCalculator.plan

        for b, derivative in enumerate(derivativeSequence):
            beam = plan.beams[b]
            diffBEV = imageTransform3D.dicomToIECGantry(diff, beam, fillValue=0., cropROI=self.roi, cropDim0=True, cropDim1=True, cropDim2=False)

            derivativeProd = np.sum(derivative.imageArray * diffBEV.imageArray, axis=2)
            derivativeProd = derivativeProd.flatten()

            derivativeProd = np.reshape(derivativeProd, plan[b].cem.gridSize)
            outCEM = copy.deepcopy(plan[b].cem)
            outCEM.imageArray = derivativeProd*alpha
            outCEMs.append(outCEM)

        return outCEMs


class DoseMaxObjective(CEMAbstractDoseFidelityTerm):
    def __init__(self, roi:ROIMask, maxDose:float, doseCalculator=None):
        super().__init__()

        self._maxDose:float = maxDose
        self.roi = roi
        self.doseCalculator = doseCalculator

    @property
    def maxDose(self):
        return self._maxDose

    @maxDose.setter
    def maxDose(self, dose):
        self._maxDose = dose

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray.astype(int))

    def getValue(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> float:
        doseImage = self.doseCalculator.computeDose(weights, cems)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.

        dose = dose.flatten()

        val = np.maximum(0., dose-self.maxDose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getCEMDerivative(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> Sequence[BiComponentCEM]:
        doseImage = self.doseCalculator.computeDose(weights, cems)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.

        diff = np.maximum(0., dose - self.maxDose)

        diffImage = copy.deepcopy(doseImage)
        diffImage.imageArray = diff

        diff = self._multiplyWithDerivative(diffImage, self.doseCalculator.computeDerivative(weights, cems), alpha=-2./self._roiVoxels)

        return diff

    def getWeightDerivative(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights, cems)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = 0.

        dose = np.flip(dose, 0)
        dose = np.flip(dose, 1)
        dose = dose.flatten(order='F')

        diff = np.maximum(0., dose - self.maxDose)
        diff = np.transpose(diff)

        beamlets = self.doseCalculator.computeBeamlets(cems)

        diff = diff @ beamlets.toSparseMatrix()
        diff *= 2. / self._roiVoxels

        diff *= beamlets.beamletRescaling

        return diff


class DoseMinObjective(CEMAbstractDoseFidelityTerm):
    def __init__(self, roi:ROIMask, minDose:float, doseCalculator=None):
        super().__init__()

        self._minDose: float = minDose
        self.roi = roi
        self.doseCalculator = doseCalculator

    @property
    def minDose(self):
        return self._minDose

    @minDose.setter
    def minDose(self, dose):
        self._minDose = dose

    @property
    def _roiVoxels(self):
        return np.count_nonzero(self.roi.imageArray)

    def getValue(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> float:
        doseImage = self.doseCalculator.computeDose(weights, cems)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = self.minDose
        dose = dose.flatten()

        val = np.maximum(0., self.minDose-dose)
        val = np.sum(val*val)/self._roiVoxels

        return val

    def getCEMDerivative(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> Sequence[BiComponentCEM]:
        doseImage = self.doseCalculator.computeDose(weights, cems)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = self.minDose

        diff = np.maximum(0., self.minDose-dose)

        diffImage = copy.deepcopy(doseImage)
        diffImage.imageArray = diff

        diff = self._multiplyWithDerivative(diffImage, self.doseCalculator.computeDerivative(weights, cems), alpha=-2./self._roiVoxels)

        return diff

    def getWeightDerivative(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> np.ndarray:
        doseImage = self.doseCalculator.computeDose(weights, cems)

        dose = np.array(doseImage.imageArray)
        dose[np.logical_not(self.roi.imageArray.astype(bool))] = self.minDose

        dose = np.flip(dose, 0)
        dose = np.flip(dose, 1)
        dose = dose.flatten(order='F')

        diff = np.maximum(0., self.minDose-dose)
        diff = np.transpose(diff)

        beamlets = self.doseCalculator.computeBeamlets(cems)

        diff = diff @ beamlets.toSparseMatrix()
        diff *= -2. / self._roiVoxels

        diff *= beamlets.beamletRescaling

        return diff
