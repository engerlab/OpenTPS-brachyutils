from typing import Optional

import numpy as np
from scipy.ndimage import gaussian_filter

from Core.Data.Images.image2D import Image2D
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.MCsquare.bdl import BDL
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D


class FluenceCalculator:
    def __init__(self):
        self.beamModel:BDL = None

    def layerFluenceAtNozzle(self, layer:PlanIonLayer, ct:Image3D, beam:PlanIonBeam, roi:Optional[ROIMask]=None) -> Image2D:
        fluenceImage = self._pointSpreadFluenceAtNozzle(layer, ct, beam, roi)

        sigmaX, sigmaY = self.beamModel.spotSizes(layer.nominalEnergy)
        sigmaX /= fluenceImage.spacing[0]
        sigmaY /= fluenceImage.spacing[1]

        # Cannot explain this
        sigmaX = sigmaX*(self.beamModel.smx-self.beamModel.nozzle_isocenter)/self.beamModel.smx
        sigmaY = sigmaY*(self.beamModel.smy-self.beamModel.nozzle_isocenter)/self.beamModel.smy

        fluenceImage.imageArray = gaussian_filter(fluenceImage.imageArray, [sigmaX, sigmaY], mode='constant', cval=0., truncate=4)

        return fluenceImage

    def _pointSpreadFluenceAtNozzle(self, layer:PlanIonLayer, ct:Image3D, beam:PlanIonBeam, roi:Optional[ROIMask]) -> Image2D:
        ctBEV = imageTransform3D.dicomToIECGantry(ct, beam, fillValue=-1024., cropROI=roi, cropDim0=True, cropDim1=True, cropDim2=False)
        isocenterBEV = imageTransform3D.dicomCoordinate2iecGantry(ct, beam, beam.isocenterPosition)

        fluence = np.zeros((ctBEV.imageArray.shape[0], ctBEV.imageArray.shape[1]))

        for i, x in enumerate(layer.spotX):
            y = layer.spotY[i]
            spotWeight = layer.spotWeights[i]

            xAtNozzle = x*(self.beamModel.smx-self.beamModel.nozzle_isocenter)/self.beamModel.smx
            yAtNozzle = y*(self.beamModel.smy-self.beamModel.nozzle_isocenter)/self.beamModel.smy

            ind = ctBEV.getVoxelIndexFromPosition(((isocenterBEV[0] + xAtNozzle), (isocenterBEV[1] - yAtNozzle), isocenterBEV[2]))
            fluence[ind[0], ind[1]] = spotWeight

        fluence / (ctBEV.spacing[0] * ctBEV.spacing[1])

        return Image2D(imageArray=fluence, spacing=ctBEV.spacing[:-1], origin=ctBEV.origin[:-1])