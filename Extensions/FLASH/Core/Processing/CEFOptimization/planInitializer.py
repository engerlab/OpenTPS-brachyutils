import copy
from math import log, exp, cos, pi
from typing import Union, Sequence

import numpy as np

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Images.rspImage import RSPImage
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
from Core.Processing.ImageProcessing.imageTransform3D import ImageTransform3D


class PlanInitializer:
    def __init__(self):
        self.calibration:AbstractCTCalibration=None
        self.ct:CTImage=None
        self.plan:RTPlan=None
        self.targetMask:ROIMask=None

    def intializePlan(self, spotSpacing:float, layerSpacing:float, targetMargin:float=0.):
        #TODO Range shifter

        roiDilated = copy.deepcopy(self.targetMask)
        roiDilated.dilate(targetMargin)

        rspImage = RSPImage.fromCT(self.ct, self.calibration, energy=100.)

        for beam in self.plan:
            beam.removeLayer(beam.layers)
            self._intializeBeam(beam, rspImage, roiDilated, spotSpacing, layerSpacing)


    def _intializeBeam(self, beam:PlanIonBeam, rspImage:RSPImage, targetROI:ROIMask, spotSpacing:float, layerSpacing:float):
        beam.isocenterPosition = targetROI.centerOfMass

        cumRSP = rspImage.computeCumulativeWEPL(beam)
        cumRSP.imageArray[np.logical_not(targetROI.imageArray.astype(bool))] = 0

        maxWEPL = cumRSP.imageArray.max()
        minWEPL = cumRSP.imageArray[cumRSP.imageArray > 0.].min()

        rangeLayers = np.arange(minWEPL-layerSpacing, maxWEPL+layerSpacing, layerSpacing)
        energyLayers = self._rangeToEnergy(rangeLayers)

        targetROIBEV = ImageTransform3D.dicomToIECGantry(targetROI, beam, 0.)
        isocenterBEV = ImageTransform3D.dicomCoordinate2iecGantry(rspImage, beam, beam.isocenterPosition)
        cumRSPBEV = ImageTransform3D.dicomToIECGantry(cumRSP, beam, 0.)
        weplMeV = self._rangeToEnergy(cumRSPBEV.imageArray)

        spotGridX, spotGridY = self._defineHexagSpotGridAroundIsocenter(spotSpacing, cumRSPBEV, isocenterBEV)
        coordGridX, coordGridY = self._pixelCoordinatedWrtIsocenter(cumRSPBEV, isocenterBEV)

        spotGridX = spotGridX.flatten()
        spotGridY = spotGridY.flatten()

        for l, energy in enumerate(energyLayers):
            if energy<=0:
                continue
            elif energy==energyLayers[0]:
                layerMask = weplMeV <= energy
            elif energy==energyLayers[-1]:
                layerMask = weplMeV > energy
            else:
                layerMask = np.logical_and(weplMeV>energy, weplMeV<=energyLayers[l+1])

            layerMask = np.sum(layerMask, axis=2).astype(bool)

            layerMask = np.logical_and(layerMask, np.sum(targetROIBEV.imageArray, axis=2).astype(bool))

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

            layer = PlanIonLayer(energy)
            for i in range(spotPosCandidates.shape[0]):
                spotPos = spotPosCandidates[i, :]
                layer.appendSpot(spotPos[0], spotPos[1], 1.)
            beam.appendLayer(layer)


    def _rangeToEnergy(self, r80:Union[float, np.ndarray])->Union[float, np.ndarray]:
        r80 /= 10 # mm -> cm

        if isinstance(r80, np.ndarray):
            r80[r80<1.]  = 1.
            return np.exp(3.464048 + 0.561372013*np.log(r80) - 0.004900892*np.log(r80)*np.log(r80) + 0.001684756748*np.log(r80)*np.log(r80)*np.log(r80))

        if r80 <= 1.:
            return 0
        else:
            return exp(3.464048 + 0.561372013 * log(r80) - 0.004900892 * log(r80)*log(r80) + 0.001684756748 * log(r80)*log(r80)*log(r80))

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