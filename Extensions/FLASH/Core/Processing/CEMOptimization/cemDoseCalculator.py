
import copy
from enum import Enum
from typing import Sequence, Union

import numpy as np

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.sparseBeamlets import SparseBeamlets
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Extensions.FLASH.Core.Processing.DoseCalculation.analyticalNoScattering import AnalyticalNoScattering
from Extensions.FLASH.Core.Processing.DoseCalculation.fluenceBasedMCsquareDoseCalculator import \
    FluenceBasedMCsquareDoseCalculator, Beamlets
from Extensions.FLASH.Core.Processing.RangeEnergy import rangeToEnergy, energyToRange

class CEMDoseCalculator:
    class DerivativeModes(Enum):
        ANALYTICAL = 'ANALYTICAL'
        DEFAULT = 'ANALYTICAL'
        MC = 'MC'

    def __init__(self):
        self.beamModel = None
        self.ctCalibration:AbstractCTCalibration = None
        self.ct:CTImage = None
        self.plan = None
        self.roi = None
        self.nbPrimaries = 5e4
        self.derivativeMode = self.DerivativeModes.DEFAULT

        self._doseCalculator = MCsquareDoseCalculator()
        self._fluenceDoseCalculator = FluenceBasedMCsquareDoseCalculator()
        self._analyticalCalculator = AnalyticalNoScattering()

        self._ctCEFForBeamlets = None
        self._weightsForBeamlets = np.array([])
        self._cemThicknessForBeamlets = np.array([])

        self._cemThicknessForDerivative = np.array([])
        self._weightsForDerivative = np.array([])

        self._sparseDerivativeCEM = None
        self._analyticalDerivative = None
        self._dose:DoseImage = None
        self._beamlets:SparseBeamlets = None
        self._firstTimeBeamletDerivative = True

        self.iteration = 0 # debug

    def kill(self):
        self._doseCalculator.kill()

    def computeDose(self, weights:np.ndarray, cemThickness:np.ndarray) -> DoseImage:
        if self._doseMustBeRecomputed(weights, cemThickness):
            self.computeBeamlets(cemThickness)
            self._updateDose(weights)

        return self._dose

    def _doseMustBeRecomputed(self, weights:np.ndarray, cemThickness:np.ndarray):
        if len(self._weightsForBeamlets)==0:
            return True

        return not(np.allclose(weights, self._weightsForBeamlets, atol=0.1)) or self._beamletsMustBeRecomputed(cemThickness)

    def _beamletsMustBeRecomputed(self, cemThickness:np.ndarray) -> bool:
        if len(self._cemThicknessForBeamlets)==0:
            return True

        return not np.allclose(cemThickness, self._cemThicknessForBeamlets, atol=0.1)

    def _updateDose(self, weights:np.ndarray):
        self._weightsForBeamlets = np.array(weights)
        self._beamlets.beamletWeights = self._weightsForBeamlets
        self._dose = self._beamlets.toDoseImage()

    def computeBeamlets(self, cemThickness: np.ndarray) -> SparseBeamlets:
        if self._beamletsMustBeRecomputed(cemThickness):
            self._updateCTForBeamletsWithCEM(cemThickness)
            self._updateBeamlets()

        return self._beamlets

    def _updateCTForBeamletsWithCEM(self, cemThickness:np.ndarray):
        self._ctCEFForBeamlets = CTImage.fromImage3D(self.ct)

        ind = 0
        for beam in self.plan:
            beam.cem.patient = None # We do not want to deepcopy patient field!
            cem = copy.deepcopy(beam.cem)

            cemArray = beam.cem.imageArray
            cemBeamVal = cemThickness[ind:ind+cemArray.shape[0]*cemArray.shape[1]]
            beam.cem.imageArray = np.reshape(cemBeamVal, (cemArray.shape[0], cemArray.shape[1]))

            [rsROI, cemROI] = beam.cem.computeROIs()

            ctArray = self._ctCEFForBeamlets.imageArray
            ctArray[cemROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.cemRSP, energy=100.)
            ctArray[rsROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.rangeShifterRSP, energy=100.)
            self._ctCEFForBeamlets.imageArray = ctArray

            ind += cemArray.shape[0]*cemArray.shape[1]

        self._cemThicknessForBeamlets = np.array(cemThickness)

    def _updateBeamlets(self):
        self._doseCalculator.beamModel = self.beamModel
        self._doseCalculator.ctCalibration = self.ctCalibration
        self._doseCalculator.nbPrimaries = self.nbPrimaries

        self._beamlets = self._doseCalculator.computeBeamlets(self._ctCEFForBeamlets, self.plan, self.roi)

    def computeDerivative(self, weights:np.ndarray, cemThickness:np.ndarray) -> Union[Beamlets, Sequence[DoseImage]]:
        if self.derivativeMode==self.DerivativeModes.ANALYTICAL:
            return self.computeAnalyticalDerivative(weights, cemThickness)
        elif self.derivativeMode==self.DerivativeModes.MC:
            return self.computeBeamletDerivative(weights, cemThickness)
        else:
            raise ValueError('derivativeMode is incorrect')

    def computeAnalyticalDerivative(self, weights:np.ndarray, cemThickness:np.ndarray) -> Sequence[DoseImage]:
        if self._derivativeMustBeRecomputed(weights, cemThickness):
            self._cemThicknessForDerivative = np.array(cemThickness)
            self._weightsForDerivative = np.array(weights)
            self._updateAnalyticalDerivative()

        return self._analyticalDerivative

    def _derivativeMustBeRecomputed(self, weights:np.ndarray, cemThickness:np.ndarray) -> bool:
        if len(self._cemThicknessForDerivative)==0:
            return True

        if len(self._weightsForDerivative)==0:
            return True

        return not(np.allclose(cemThickness, self._cemThicknessForDerivative, atol=0.1) and np.allclose(weights, self._weightsForDerivative, atol=0.1))

    def _updateAnalyticalDerivative(self):
        deltaR = 0.1

        self._analyticalCalculator.beamModel = self.beamModel
        self._analyticalCalculator.ctCalibration = self.ctCalibration

        plan = copy.deepcopy(self.plan)
        plan.spotWeights = self._weightsForDerivative

        ind = 0
        for beam in plan:
            cemArray = beam.cem.imageArray
            cemBeamVal = self._cemThicknessForDerivative[ind:ind+cemArray.shape[0]*cemArray.shape[1]]
            beam.cem.imageArray = np.reshape(cemBeamVal, (cemArray.shape[0], cemArray.shape[1]))

            ind += cemArray.shape[0]*cemArray.shape[1]

        doseSequence = self._analyticalCalculator.computeDosePerBeam(self.ct, plan, self.roi)

        plan2 = self._lowerPlanEnergy(plan, deltaR=deltaR)
        doseSequence2 = self._analyticalCalculator.computeDosePerBeam(self.ct, plan2, self.roi)

        derivSequence = []
        for i, dose in enumerate(doseSequence):
            dose.imageArray = (dose.imageArray - doseSequence2[i].imageArray)/deltaR
            outDose = DoseImage.fromImage3D(dose)
            outDose = imageTransform3D.dicomToIECGantry(outDose, plan.beams[i], fillValue=0., cropROI=self.roi, cropDim0=True, cropDim1=True, cropDim2=False)
            derivSequence.append(outDose)

        self._analyticalDerivative = derivSequence

    def computeBeamletDerivative(self, weights:np.ndarray, cemThickness: np.ndarray) -> Beamlets:
        if self._firstTimeBeamletDerivative or not (np.array_equal(cemThickness, self._cemThicknessForDerivative) and np.array_equal(weights, self._weightsForDerivative)):
            self._cemThicknessForDerivative = cemThickness
            self._weightsForDerivative = weights
            self._updateBeamletDerivative()

            self._firstTimeBeamletDerivative = False

        return self._sparseDerivativeCEM


    def _updateBeamletDerivative(self):
        self._fluenceDoseCalculator.beamModel = self.beamModel
        self._fluenceDoseCalculator.ctCalibration = self.ctCalibration
        self._fluenceDoseCalculator.nbPrimaries = 1e4

        # We lower the energy in computeBeamlets so that output sparseBeamle ts has exactly the same shape as that of beamlets1
        beamlets = self._fluenceDoseCalculator.computeBeamlets(self._ctCEFForBeamlets, self.plan, roi=self.roi)
        beamletsE2 = self._fluenceDoseCalculator.computeBeamlets(self._ctCEFForBeamlets, self.plan, roi=self.roi, deltaR=-1.)

        sparseBeamlets = beamlets.sparseBeamlets
        sparseBeamlets.setUnitaryBeamlets(sparseBeamlets.toSparseMatrix() - beamletsE2.sparseBeamlets.toSparseMatrix())
        beamlets.sparseBeamlets = sparseBeamlets

        self._sparseDerivativeCEM = beamlets

    def _lowerPlanEnergy(self, plan:RTPlan, deltaR:float=1.) -> RTPlan:
        plan2 = copy.deepcopy(plan)

        for beam in plan2:
            for layer in beam:
                layer.nominalEnergy = rangeToEnergy(energyToRange(layer.nominalEnergy)-deltaR)

        return plan2
