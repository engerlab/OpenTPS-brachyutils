import copy
from typing import Optional, Sequence, Union

import numpy as np
from matplotlib import pyplot as plt
from scipy.ndimage import gaussian_filter

from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.MCsquare.mcsquareConfig import MCsquareConfig
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing.imageTransform3D import ImageTransform3D


class FluenceBasedMCsquareDoseCalculator(MCsquareDoseCalculator):
    HU_AIR = -1024
    SPOT_WEIGHT_THRESHOLD = 0.01

    def __init__(self):
        super().__init__()

        self._distToIsocenter = 0.0

    @property
    def distanceToIsocenter(self) -> float:
        return self._distToIsocenter

    @distanceToIsocenter.setter
    def distanceToIsocenter(self, dist: float):
        self._distToIsocenter = dist

    def computeDose(self, ct:CTImage, plan: RTPlan) -> DoseImage:
        return super().computeDose(ct, self._fluencePlan)

    def computeBeamlets(self, ct:CTImage, plan:RTPlan, roi:Optional[ROIMask] = None):
        self._ct = ct
        self._plan = self._fluencePlan
        self._roi = roi
        self._config = self._bemletComputationConfig

        self._writeFilesToSimuDir()
        self._cleanDir(self._outputDir)
        self._startMCsquare()

        beamletDose = self._importBeamlets()

        return beamletDose

    @property
    def _fluencePlan(self) -> RTPlan:
        newPlan = copy.deepcopy(self._plan)

        for beam in newPlan:
            ctBEV = ImageTransform3D.dicomToIECGantry(self._ct, beam, self.HU_AIR)
            isocenterBEV = ImageTransform3D.dicomCoordinate2iecGantry(self._ct, beam, beam.isocenterPosition)

            for layer in beam:
                fluence = self._layerFluence(beam, layer)
                fluence = fluence*layer.meterset/np.sum(fluence)

                layer.removeSpot(layer.spotX, layer.spotY) # Empty layer
                x, y = np.meshgrid(range(fluence.shape[0]), range(fluence.shape[1]))

                for i in range(x.shape[0]):
                    for j in range(x.shape[1]):
                        if fluence[x[i, j], y[i, j]]>self.SPOT_WEIGHT_THRESHOLD:
                            pos = ctBEV.getPositionFromVoxelIndex((x[i, j], y[i, j], isocenterBEV[2]))
                            pos0 = pos[0] - isocenterBEV[0]
                            pos1 = -pos[1] + isocenterBEV[1]

                            layer.appendSpot(pos0, pos1, fluence[i, j])
        return newPlan

    def _layerFluence(self, beam:PlanIonBeam, layer:PlanIonLayer):
        xAtDist, yAtDist = self._xyAtDistFromIso(layer.spotX, layer.spotY)
        xyAtDist = zip(xAtDist, yAtDist)

        isocenterBEV = ImageTransform3D.dicomCoordinate2iecGantry(self._ct, beam, beam.isocenterPosition)
        xyInds = [self._ct.getVoxelIndexFromPosition((isocenterBEV[0]+xy[0], isocenterBEV[1]-xy[1], isocenterBEV[2]+self._distToIsocenter)) for xy in xyAtDist]

        ctBEV = ImageTransform3D.dicomToIECGantry(self._ct, beam, self.HU_AIR)
        fluence = np.zeros((ctBEV.imageArray.shape[0], ctBEV.imageArray.shape[1]))

        for i, weight in enumerate(layer.spotWeights):
            xyInd = xyInds[i]
            fluence[xyInd[0], xyInd[1]] = weight

        initialFluence = fluence / (ctBEV.spacing[0] * ctBEV.spacing[1])

        sigmaX, sigmaY = self.beamModel.spotSizes(layer.nominalEnergy, z=0.)
        sigmaX /= ctBEV.spacing[0]
        sigmaY /= ctBEV.spacing[1]

        fluence = gaussian_filter(initialFluence, [sigmaX, sigmaY], mode='constant', cval=0., truncate=4)

        return fluence

    def _xyAtDistFromIso(self, x:Union[float, Sequence[float]], y:Union[float, Sequence[float]]) -> tuple[Sequence[float], Sequence[float]]:
        x = (np.array(x) / self.beamModel.smx)*(self.beamModel.smx - self._distToIsocenter)
        y = (np.array(y) / self.beamModel.smy)*(self.beamModel.smy - self._distToIsocenter)

        return (x, y)

    @property
    def _bemletComputationConfig(self) -> MCsquareConfig:
        config = super()._bemletComputationConfig
        
        config["NoSpotSize"] = True

        return config