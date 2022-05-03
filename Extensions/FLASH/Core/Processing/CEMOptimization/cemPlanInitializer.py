from math import cos, pi
from typing import Sequence

import numpy as np

from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.rtPlan import RTPlan
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam


class CEMPlanInitializer:
    def __init__(self):
        self.plan:RTPlan=None
        self.targetMask:ROIMask=None

    def intializePlan(self, spotSpacing:float, targetMargin:float=0.):
        roiDilated = ROIMask.fromImage3D(self.targetMask)
        roiDilated.dilate(targetMargin)

        for beam in self.plan:
            self._intializeBeam(beam, roiDilated, spotSpacing)


    def _intializeBeam(self, beam:CEMBeam, targetROI:ROIMask, spotSpacing:float):
        beam.isocenterPosition = targetROI.centerOfMass

        targetROIBEV = imageTransform3D.dicomToIECGantry(targetROI, beam, 0.)
        isocenterBEV = imageTransform3D.dicomCoordinate2iecGantry(targetROI, beam, beam.isocenterPosition)

        spotGridX, spotGridY = self._defineHexagSpotGridAroundIsocenter(spotSpacing, targetROIBEV, isocenterBEV)
        coordGridX, coordGridY = self._pixelCoordinatedWrtIsocenter(targetROIBEV, isocenterBEV)

        spotGridX = spotGridX.flatten()
        spotGridY = spotGridY.flatten()

        for layer in beam:
            layerMask = np.sum(targetROIBEV.imageArray, axis=2).astype(bool)

            coordX = coordGridX[layerMask]
            coordY = coordGridY[layerMask]

            coordX = coordX.flatten()
            coordY = coordY.flatten()

            x2 = np.matlib.repmat(np.reshape(spotGridX, (spotGridX.shape[0], 1)), 1, coordX.shape[0]) \
                 - np.matlib.repmat(np.transpose(coordX), spotGridX.shape[0], 1)
            y2 = np.matlib.repmat(np.reshape(spotGridY, (spotGridY.shape[0], 1)), 1, coordY.shape[0]) \
                 - np.matlib.repmat(np.transpose(coordY), spotGridY.shape[0], 1)

            ind = (x2*x2+y2*y2).argmin(axis=0)

            spotPosCandidates = np.unique(np.array(list(zip(spotGridX[ind], -spotGridY[ind]))), axis=0)

            for i in range(spotPosCandidates.shape[0]):
                spotPos = spotPosCandidates[i, :]
                layer.addToSpot(spotPos[0], spotPos[1], 0.) # We do not append spot but rather add it because append throws an exception if already exists

            beam.spotWeights = np.ones(beam.spotWeights.shape)

    def _defineHexagSpotGridAroundIsocenter(self, spotSpacing:float, imageBEV:Image3D, isocenterBEV:Sequence[float]):
        origin = imageBEV.origin
        end = imageBEV.origin + imageBEV.spacing * imageBEV.imageArray.shape

        spotGridSpacing = [spotSpacing/2., spotSpacing*cos(pi/6.)]

        xFromIsoToOrigin = np.arange(isocenterBEV[0], origin[0], -spotGridSpacing[0])
        xFromOriginToIso = np.flipud(xFromIsoToOrigin)
        xFromIsoToEnd = np.arange(isocenterBEV[0]+spotGridSpacing[0], end[0], spotGridSpacing[0])
        yFromIsoToOrigin = np.arange(isocenterBEV[1], origin[1], -spotGridSpacing[1])
        yFromOriginToIso = np.flipud(yFromIsoToOrigin)
        yFromIsoToEnd = np.arange(isocenterBEV[1]+spotGridSpacing[1], end[1], spotGridSpacing[1])

        x = np.concatenate((xFromOriginToIso, xFromIsoToEnd))
        y = np.concatenate((yFromOriginToIso, yFromIsoToEnd))

        spotGridX, spotGridY = np.meshgrid(x, y)

        spotGridX = spotGridX-isocenterBEV[0]
        spotGridY = spotGridY-isocenterBEV[1]

        isoInd0 = xFromOriginToIso.shape[0] # index of isocenter
        isoInd1 = yFromOriginToIso.shape[0] # index of isocenter

        heaxagonalMask = np.zeros(spotGridX.shape)
        heaxagonalMask[(isoInd0+1)%2::2, (isoInd1+1)%2:2] = 1
        heaxagonalMask[1-(isoInd0+1)%2::2, 1-(isoInd1+1)%2::2] = 1

        spotGridX = spotGridX[heaxagonalMask.astype(bool)]
        spotGridY = spotGridY[heaxagonalMask.astype(bool)]

        return spotGridX, spotGridY

    def _pixelCoordinatedWrtIsocenter(self, imageBEV:Image3D, isocenterBEV:Sequence[float]):
        origin = imageBEV.origin
        end = imageBEV.origin + imageBEV.spacing*imageBEV.imageArray.shape

        x = np.arange(origin[0], end[0], imageBEV.spacing[0])
        y = np.arange(origin[1], end[1], imageBEV.spacing[1])
        [coordGridX, coordGridY] = np.meshgrid(x, y)
        coordGridX = np.transpose(coordGridX)
        coordGridY = np.transpose(coordGridY)

        coordGridX = coordGridX - isocenterBEV[0]
        coordGridY = coordGridY - isocenterBEV[1]

        return coordGridX, coordGridY
