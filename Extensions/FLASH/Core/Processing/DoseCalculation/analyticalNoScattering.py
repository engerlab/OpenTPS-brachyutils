from math import exp, log
from typing import Union, Tuple

import numpy as np
from scipy.interpolate import interpolate

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.rspImage import RSPImage
from Core.Data.MCsquare.bdl import BDL
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
from Core.Processing.DoseCalculation.abstractDoseCalculator import AbstractDoseCalculator
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing.imageTransform3D import ImageTransform3D
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam
from Extensions.FLASH.Core.Processing.DoseCalculation.MCsquare.fluenceCalculator import FluenceCalculator


class AnalyticalNoScattering(AbstractDoseCalculator):
    def __init__(self):
        super().__init__()

        self.beamModel:BDL = None
        self.ctCalibration:AbstractCTCalibration = None
        self.referenceEnergy = 226 # MeV

        self._referenceIDDEnergy = None
        self._referenceIDDX = None
        self._shiftReferenceIDD = None
        self._shiftDerivIDD = None

    def computeDose(self, ct:CTImage, plan:RTPlan) -> DoseImage:
        fluenceCalculator = FluenceCalculator()
        fluenceCalculator.beamModel = self.beamModel

        self._computeReferenceIDD()

        rsp = RSPImage.fromCT(ct, self.ctCalibration)
        doseImage = DoseImage.fromImage3D(ct)
        doseImage.imageArray = np.zeros(doseImage.imageArray.shape)

        for beam in plan:
            cumRSP = rsp.computeCumulativeWEPL(beam)
            cumRSP = ImageTransform3D.dicomToIECGantry(cumRSP, beam, fillValue=0.)

            doseImageBEV = DoseImage.fromImage3D(cumRSP)
            doseImageArray = np.zeros(doseImageBEV.imageArray.shape)

            wetBeforeCT = self._wetBeforeCT(beam)

            for layer in beam:
                fluence = fluenceCalculator.layerFluenceAtNozzle(layer, ct, beam)
                fluence = fluence.imageArray

                layerDose, layerDeriv = self._doseOnReferenceIDDGrid(wetBeforeCT, layer.nominalEnergy)

                for i in range(wetBeforeCT.shape[0]):
                    for j in range(wetBeforeCT.shape[1]):
                        f = interpolate.interp1d(self._referenceIDDX, np.squeeze(layerDose[i, j, :]), kind='linear', fill_value=0., assume_sorted=True)
                        doseImageArray[i, j, :] += fluence[i, j] * f(np.squeeze(cumRSP.imageArray[i, j, :]))

            doseImageBEV.imageArray = doseImageArray
            doseImageDicom = ImageTransform3D.iecGantryToDicom(doseImageBEV, beam, fillValue=0.)

            doseImage.imageArray = doseImage.imageArray+doseImageDicom.imageArray

            return doseImage


    def _wetBeforeCT(self, beam:PlanIonBeam) -> Union[float, np.ndarray]:
        wet = 0.

        if not beam.rangeShifter is None:
            wet += beam.rangeShifter.WET

        if isinstance(beam, CEMBeam):
            wet += beam.cem.imageArray

        return wet

    def _doseOnReferenceIDDGrid(self, wetBeforeCT:np.ndarray, energy:float) -> Tuple[np.ndarray, np.ndarray]:
        wetBeforeCT = wetBeforeCT + self._energy_to_range(self.referenceEnergy) - self._energy_to_range(energy)

        layerDose = np.zeros((wetBeforeCT.shape[0], wetBeforeCT.shape[1], self._shiftReferenceIDD(0).shape[0]))
        layerDeriv = np.zeros(layerDose.shape)

        for i in range(wetBeforeCT.shape[0]):
            for j in range(wetBeforeCT.shape[1]):
                layerDose[i, j, :] = self._shiftReferenceIDD(wetBeforeCT[i, j])
                layerDeriv[i, j, :] = self._shiftDerivIDD(wetBeforeCT[i, j])

        layerDose = layerDose * self.beamModel.computeMU2Protons(energy) / self.beamModel.computeMU2Protons(self.referenceEnergy)
        layerDeriv = layerDeriv * self.beamModel.computeMU2Protons(energy) / self.beamModel.computeMU2Protons(self.referenceEnergy)

        return layerDose, layerDeriv

    def _findIndexOfFluenceBoundingBox(self, fluence:np.ndarray) -> Tuple[int, int, int, int]:
        xFirst = 0
        xLast = 0
        yFirst = 0
        yLast = 0

        for xFirst in range(fluence.shape[0]):
            if np.any(fluence[xFirst, :]):
                xFirst -= 1
                break

        for xLast in np.arange(fluence.shape[0]-1, 0-1, -1):
            if np.any(fluence[xLast, :]):
                xLast += 1
                break

        for yFirst in range(fluence.shape[0]):
            if np.any(fluence[:, yFirst]):
                yFirst -= 1
                break

        for yLast in np.arange(fluence.shape[0]-1, 0-1, -1):
            if np.any(fluence[:, yLast]):
                yLast += 1
                break

        return xFirst, xLast, yFirst, yLast

    def _computeReferenceIDD(self):
        if self._referenceIDDEnergy == self.referenceEnergy:
            return

        ctLength = round(self._energy_to_range(self.referenceEnergy)) + 10 # 10 is just amargin
        if not ctLength%2:
            ctLength += 1

        huWater = self.ctCalibration.convertRSP2HU(1.)
        data = huWater * np.ones((ctLength, ctLength, ctLength))
        spacing = (1., 1., 1.)
        origin = (0., 0., 0.)

        ct = CTImage(imageArray=data, spacing=spacing, origin=origin)

        mu = 1.
        plan = RTPlan()
        beam = PlanIonBeam()
        beam.gantryAngle = 0.
        beam.isocenterPosition = np.array((ctLength, ctLength, ctLength))/2.
        layer = PlanIonLayer()
        layer.nominalEnergy = self.referenceEnergy
        layer.appendSpot(0, 0, mu)
        beam.appendLayer(layer)
        plan.appendBeam(beam)

        doseCalculator = MCsquareDoseCalculator()
        doseCalculator.beamModel = self.beamModel
        doseCalculator.ctCalibration = self.ctCalibration
        doseCalculator.nbPrimaries = 1e6

        doseImage = doseCalculator.computeDose(ct, plan)

        refIDD = np.squeeze(np.sum(np.sum(doseImage.imageArray, 2), 0)) / mu

        refIDD[0] = refIDD[1] # Useful for when we have to extrapolate.
        refIDD[-1] = 0
        refIDD[-2] = 0

        self._referenceIDDX = np.array(range(refIDD.shape[0])) + 1.

        depth10 = np.arange(0, np.max(self._referenceIDDX), 0.1) + 1.
        f = interpolate.interp1d(self._referenceIDDX, refIDD, kind='linear', fill_value=0., assume_sorted=True)
        ref10 = f(depth10)
        f = interpolate.interp1d(depth10[:-1], (ref10[1:]-ref10[:-1])/(depth10[1]-depth10[0]), kind='linear', fill_value=0., assume_sorted=True)
        derivIDD = f(self._referenceIDDX)

        self._referenceIDDEnergy = self.referenceEnergy
        referenceIDDFunction = interpolate.interp1d(self._referenceIDDX, refIDD, kind='linear', fill_value=0., assume_sorted=True)
        derivIDDFunction = interpolate.interp1d(self._referenceIDDX, derivIDD, kind='linear', fill_value=0., assume_sorted=True)

        self._shiftReferenceIDD = lambda wet: referenceIDDFunction(self._referenceIDDX+wet)
        self._shiftDerivIDD = lambda wet: derivIDDFunction(self._referenceIDDX+wet)

    def _rangeToEnergy(self, r80:Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        r80 /= 10 # mm -> cm

        if isinstance(r80, np.ndarray):
            r80[r80<1.]  = 1.
            return np.exp(3.464048 + 0.561372013*np.log(r80) - 0.004900892*np.log(r80)*np.log(r80) + 0.001684756748*np.log(r80)*np.log(r80)*np.log(r80))

        if r80 <= 1.:
            return 0
        else:
            return exp(3.464048 + 0.561372013*log(r80) - 0.004900892*log(r80)*log(r80) + 0.001684756748*log(r80)*log(r80)*log(r80))

    def _energy_to_range(self, energy:Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        if isinstance(energy, np.ndarray):
            energy[energy < 1.] = 1.
            r80 = np.exp(-5.5064 + 1.2193*np.log(energy) + 0.15248*np.log(energy)*np.log(energy) - 0.013296*np.log(energy)*np.log(energy)*np.log(energy))

        if energy <= 1:
            r80 = 0
        else:
            r80 = exp(-5.5064 + 1.2193*log(energy) + 0.15248*log(energy)*log(energy) - 0.013296*log(energy)*log(energy)*log(energy))

        return r80
