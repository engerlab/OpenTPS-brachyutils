
import copy
from enum import Enum
from typing import Sequence, Union

import numpy as np

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.sparseBeamlets import SparseBeamlets
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Extensions.FLASH.Core.Data.cem import BiComponentCEM
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

    def computeDose(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> DoseImage:
        if self._doseMustBeRecomputed(weights, cems):
            self.computeBeamlets(cems)
            self._updateDose(weights)

        return self._dose

    def _doseMustBeRecomputed(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]):
        if len(self._weightsForBeamlets)==0:
            return True

        return not(np.allclose(weights, self._weightsForBeamlets, atol=0.1)) or self._beamletsMustBeRecomputed(cems)

    def _beamletsMustBeRecomputed(self, cems:Sequence[BiComponentCEM]) -> bool:
        if len(self._cemThicknessForBeamlets)==0:
            return True

        return not np.allclose(self._flattenCEMs(cems), self._cemThicknessForBeamlets, atol=0.1)

    def _flattenCEMs(self, cems:Sequence[BiComponentCEM]):
        cemVals = None

        for cem in cems:
            if cemVals is None:
                cemVals = cem.imageArray.flatten()
            else:
                cemVals = np.concatenate(cem.imageArray.flatten())

        return cemVals

    def _updateDose(self, weights:np.ndarray):
        self._weightsForBeamlets = np.array(weights)
        self._beamlets.beamletWeights = self._weightsForBeamlets
        self._dose = self._beamlets.toDoseImage()

    def computeBeamlets(self, cems:Sequence[BiComponentCEM]) -> SparseBeamlets:
        if self._beamletsMustBeRecomputed(cems):
            self._updateCTForBeamletsWithCEM(cems)
            self._updateBeamlets()
            self._cemThicknessForBeamlets = np.array(self._flattenCEMs(cems))

        return self._beamlets

    def _updateCTForBeamletsWithCEM(self, cems:Sequence[BiComponentCEM]):
        self._ctCEFForBeamlets = CTImage.fromImage3D(self.ct)

        for b, cem in enumerate(cems):
            beam = self.plan[b]

            beam.cem.imageArray = cem.imageArray

            [rsROI, cemROI] = beam.cem.computeROIs()

            imageTransform3D.intersect(rsROI, self._ctCEFForBeamlets, fillValue=0, inPlace=True)
            imageTransform3D.intersect(cemROI, self._ctCEFForBeamlets, fillValue=0, inPlace=True)

            ctArray = self._ctCEFForBeamlets.imageArray
            ctArray[cemROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.cemRSP, energy=100.)
            ctArray[rsROI.imageArray.astype(bool)] = self.ctCalibration.convertRSP2HU(cem.rangeShifterRSP, energy=100.)
            self._ctCEFForBeamlets.imageArray = ctArray

    def _updateBeamlets(self):
        self._doseCalculator.beamModel = self.beamModel
        self._doseCalculator.ctCalibration = self.ctCalibration
        self._doseCalculator.nbPrimaries = self.nbPrimaries

        self._beamlets = self._doseCalculator.computeBeamlets(self._ctCEFForBeamlets, self.plan, self.roi)

    def computeDerivative(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> Union[Beamlets, Sequence[DoseImage]]:
        if self.derivativeMode==self.DerivativeModes.ANALYTICAL:
            return self.computeAnalyticalDerivative(weights, cems)
        elif self.derivativeMode==self.DerivativeModes.MC:
            return self.computeBeamletDerivative(weights, cems)
        else:
            raise ValueError('derivativeMode is incorrect')

    def computeAnalyticalDerivative(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> Sequence[DoseImage]:
        if self._derivativeMustBeRecomputed(weights, cems):
            self._cemThicknessForDerivative = self._flattenCEMs(cems)
            self._weightsForDerivative = np.array(weights)
            self._updateAnalyticalDerivative(cems)

        return self._analyticalDerivative

    def _derivativeMustBeRecomputed(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> bool:
        if len(self._cemThicknessForDerivative)==0:
            return True

        if len(self._weightsForDerivative)==0:
            return True

        return not(np.allclose(self._flattenCEMs(cems), self._cemThicknessForDerivative, atol=0.1) and np.allclose(weights, self._weightsForDerivative, atol=0.1))

    def _updateAnalyticalDerivative(self, cems:Sequence[BiComponentCEM]):
        deltaR = 1

        self._analyticalCalculator.beamModel = self.beamModel
        self._analyticalCalculator.ctCalibration = self.ctCalibration

        plan = copy.deepcopy(self.plan)
        plan.spotWeights = self._weightsForDerivative

        for b, cem in enumerate(cems):
            beam = plan[b]
            beam.cem.imageArray = cem.imageArray

        doseSequence = self._analyticalCalculator.computeDosePerBeam(self.ct, plan, self.roi)

        plan2 = self._lowerPlanEnergy(plan, deltaR=deltaR)
        doseSequence2 = self._analyticalCalculator.computeDosePerBeam(self.ct, plan2, self.roi)

        derivSequence = []
        for i, dose in enumerate(doseSequence):
            dose = Image3D.fromImage3D(dose)
            dose.imageArray = (dose.imageArray - doseSequence2[i].imageArray)/deltaR
            outDose = DoseImage.fromImage3D(dose)
            outDose = imageTransform3D.dicomToIECGantry(outDose, plan.beams[i], fillValue=0., cropROI=self.roi, cropDim0=True, cropDim1=True, cropDim2=False)
            derivSequence.append(outDose)

        self._analyticalDerivative = derivSequence

    def computeBeamletDerivative(self, weights:np.ndarray, cems:Sequence[BiComponentCEM]) -> Beamlets:
        flattenedCEMs = self._flattenCEMs(cems)

        if self._firstTimeBeamletDerivative or not (np.array_equal(flattenedCEMs, self._cemThicknessForDerivative)
                                                    and np.array_equal(weights, self._weightsForDerivative)):
            self._weightsForDerivative = weights
            self._updateCTForBeamletsWithCEM(cems)
            self._updateBeamletDerivative()
            self._cemThicknessForDerivative = flattenedCEMs

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
