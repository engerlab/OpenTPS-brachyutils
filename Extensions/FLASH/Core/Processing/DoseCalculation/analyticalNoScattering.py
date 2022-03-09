from typing import Union, Tuple

import numpy as np

from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.MCsquare.bdl import BDL
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.rtPlan import RTPlan
from Core.Processing.DoseCalculation.abstractDoseCalculator import AbstractDoseCalculator
from Core.Processing.ImageProcessing.imageTransform3D import ImageTransform3D
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam
from Extensions.FLASH.Core.Processing.DoseCalculation.MCsquare.fluenceCalculator import FluenceCalculator


class AnalyticalNoScattering(AbstractDoseCalculator):
    def __init__(self):
        super().__init__()

        self.beamModel:BDL = None

    def computeDose(self, ct:CTImage, plan:RTPlan) -> DoseImage:
        resDose = 0
        derivDose = 0

        for beam in plan:
            ctBEV = ImageTransform3D.dicomToIECGantry(ct, beam, fillValue=-1024.)

            wet = self._wetBeforeCT(beam)
            fluence = self._fluenceAtNozzle(ct, beam)



    def _wetBeforeCT(self, beam:PlanIonBeam) -> Union[float, np.ndarray]:
        wet = 0.

        if not beam.rangeShifter is None:
            wet += beam.rangeShifter.WET

        if isinstance(beam, CEMBeam):
            wet += beam.cem.imageArray

        return wet

    def _fluenceAtNozzle(self, ct:CTImage, beam:PlanIonBeam) -> np.ndarray:
        fluenceCalculator = FluenceCalculator()
        fluenceCalculator.beamModel = self.beamModel

        fluenceAtNozzle = 0.

        for layer in beam:
            fluence = fluenceCalculator.layerFluenceAtNozzle(layer, ct, beam)
            fluenceAtNozzle += fluence.imageArray

        if not isinstance(fluenceAtNozzle, np.ndarray):
            raise Exception('Beam is empty.')

        return fluenceAtNozzle

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
