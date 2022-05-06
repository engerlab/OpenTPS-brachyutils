
from typing import Union, Tuple, Sequence

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
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam
from Extensions.FLASH.Core.Processing.DoseCalculation.MCsquare.fluenceCalculator import FluenceCalculator
from Extensions.FLASH.Core.Processing.RangeEnergy import energyToRange


class AnalyticalNoScattering(AbstractDoseCalculator):
    def __init__(self):
        super().__init__()

        self._beamModel = None
        self._ctCalibration = None
        self.referenceEnergy = 226 # MeV

        self._referenceIDDEnergy = None
        self._referenceIDDX = None
        self._shiftReferenceIDD = None
        self._shiftDerivIDD = None

    @property
    def beamModel(self) -> BDL:
        return self._beamModel

    @beamModel.setter
    def beamModel(self, bdl:BDL):
        self._beamModel = bdl

    @property
    def ctCalibration(self) -> AbstractCTCalibration:
        return self._ctCalibration

    @ctCalibration.setter
    def ctCalibration(self, calibration:AbstractCTCalibration):
        self._ctCalibration = calibration

    def computeDose(self, ct:CTImage, plan:RTPlan) -> DoseImage:
        outImage = DoseImage.fromImage3D(ct)
        outImage.imageArray = np.zeros(outImage.imageArray.shape)

        for doseImage in self.computeDosePerBeam(ct, plan):
            outImage.imageArray = outImage.imageArray + doseImage.imageArray

        return outImage

    def computeDosePerBeam(self, ct:CTImage, plan:RTPlan) -> Sequence[DoseImage]:
        self._computeReferenceIDD()

        doseImages = []
        for beam in plan:
            doseImageDicom = self._computeDoseForBeam(ct, beam)
            imageTransform3D.intersect(doseImageDicom, ct, inPlace=True, fillValue=0.)
            doseImages.append(doseImageDicom)

        return doseImages

    def _computeDoseForBeam(self, ct:CTImage, beam:PlanIonBeam) -> DoseImage:
        fluenceCalculator = FluenceCalculator()
        fluenceCalculator.beamModel = self.beamModel

        rsp = RSPImage.fromCT(ct, self.ctCalibration)

        cumRSP = rsp.computeCumulativeWEPL(beam)
        cumRSP = imageTransform3D.dicomToIECGantry(cumRSP, beam, fillValue=0.)

        doseImageBEV = DoseImage.fromImage3D(cumRSP)
        doseImageArray = np.zeros(doseImageBEV.imageArray.shape)

        wetBeforeCT = self._wetBeforeCT(beam)

        for layer in beam:
            fluence = fluenceCalculator.layerFluenceAtNozzle(layer, ct, beam)
            fluence = fluence.imageArray

            layerDose, layerDeriv = self._doseOnReferenceIDDGrid(wetBeforeCT, layer.nominalEnergy)

            for i in range(wetBeforeCT.shape[0]):
                for j in range(wetBeforeCT.shape[1]):
                    f = interpolate.interp1d(self._referenceIDDX, np.squeeze(layerDose[i, j, :]), kind='linear',
                                             fill_value='extrapolate', assume_sorted=True)
                    doseImageArray[i, j, :] += fluence[i, j] * f(np.squeeze(cumRSP.imageArray[i, j, :]))

        doseImageBEV.imageArray = doseImageArray
        doseImageDicom = imageTransform3D.iecGantryToDicom(doseImageBEV, beam, fillValue=0.)

        return doseImageDicom

    def _wetBeforeCT(self, beam:PlanIonBeam) -> Union[float, np.ndarray]:
        wet = 0.

        if not beam.rangeShifter is None:
            wet += beam.rangeShifter.WET

        if isinstance(beam, CEMBeam):
            wet += beam.cem.imageArray

        return wet

    def _doseOnReferenceIDDGrid(self, wetBeforeCT:np.ndarray, energy:float) -> Tuple[np.ndarray, np.ndarray]:
        wetBeforeCT = wetBeforeCT + energyToRange(self.referenceEnergy) - energyToRange(energy)

        layerDose = np.zeros((wetBeforeCT.shape[0], wetBeforeCT.shape[1], self._shiftReferenceIDD(0).shape[0]))
        layerDeriv = np.zeros(layerDose.shape)

        for i in range(wetBeforeCT.shape[0]):
            for j in range(wetBeforeCT.shape[1]):
                layerDose[i, j, :] = self._shiftReferenceIDD(wetBeforeCT[i, j])
                layerDeriv[i, j, :] = self._shiftDerivIDD(wetBeforeCT[i, j])

        layerDose = layerDose * self.beamModel.computeMU2Protons(energy) / self.beamModel.computeMU2Protons(self.referenceEnergy)
        layerDeriv = layerDeriv * self.beamModel.computeMU2Protons(energy) / self.beamModel.computeMU2Protons(self.referenceEnergy)

        return layerDose, layerDeriv

    def _computeReferenceIDD(self):
        if self._referenceIDDEnergy == self.referenceEnergy:
            return

        ctLength = round(energyToRange(self.referenceEnergy)) + 10 # 10 is just amargin
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

        # Useful for when we have to extrapolate:
        refIDD[0] = refIDD[1]
        refIDD[-1] = 0
        refIDD[-2] = 0

        self._referenceIDDX = np.array(range(refIDD.shape[0])) + 1.

        depth10 = np.arange(0, np.max(self._referenceIDDX), 0.1) + 1.
        f = interpolate.interp1d(self._referenceIDDX, refIDD, kind='linear', fill_value='extrapolate', assume_sorted=True)
        ref10 = f(depth10)
        f = interpolate.interp1d(depth10[:-1], (ref10[1:]-ref10[:-1])/(depth10[1]-depth10[0]), kind='linear', fill_value='extrapolate', assume_sorted=True)
        derivIDD = f(self._referenceIDDX)

        self._referenceIDDEnergy = self.referenceEnergy
        referenceIDDFunction = interpolate.interp1d(self._referenceIDDX, refIDD, kind='linear', fill_value='extrapolate', assume_sorted=True)
        derivIDDFunction = interpolate.interp1d(self._referenceIDDX, derivIDD, kind='linear', fill_value='extrapolate', assume_sorted=True)

        self._shiftReferenceIDD = lambda wet: referenceIDDFunction(self._referenceIDDX+wet)
        self._shiftDerivIDD = lambda wet: derivIDDFunction(self._referenceIDDX+wet)
