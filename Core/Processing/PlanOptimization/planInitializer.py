from math import cos, pi
from typing import Sequence

import numpy as np

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Images.rspImage import RSPImage
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Extensions.FLASH.Core.Processing.RangeEnergy import rangeToEnergy


class BeamInitializerBEV:
    def __init__(self):
        self.spotSpacing = 5.
        self.layerSpacing = 2.
        self.targetMargin = 0.

        self.calibration:AbstractCTCalibration=None

    def intializeBeam(self, beam:PlanIonBeam, ctBEV:CTImage, targetMaskBEV:ROIMask):
        #TODO Range shifter

        roiDilated = ROIMask.fromImage3D(targetMaskBEV)
        roiDilated.dilate(radius=self.targetMargin)

        rspImage = RSPImage.fromCT(ctBEV, self.calibration, energy=100.)

        if beam.isocenterPosition is None:
            beam.isocenterPosition = targetMaskBEV.centerOfMass

        cumRSPBEV = RSPImage.fromImage3D(rspImage)
        cumRSPArray =  np.cumsum(cumRSPBEV.imageArray, axis=2)*cumRSPBEV.spacing[2]
        cumRSPArray[np.logical_not(roiDilated.imageArray.astype(bool))]= 0
        cumRSPBEV.imageArray = cumRSPArray

        maxWEPL = cumRSPBEV.imageArray.max()
        minWEPL = cumRSPBEV.imageArray[cumRSPBEV.imageArray > 0.].min()

        rangeLayers = np.arange(minWEPL-self.layerSpacing, maxWEPL+self.layerSpacing, self.layerSpacing)
        energyLayers = rangeToEnergy(rangeLayers)

        weplMeV = rangeToEnergy(cumRSPBEV.imageArray)

        spotGridX, spotGridY = self._defineHexagSpotGridAroundIsocenter(self.spotSpacing, cumRSPBEV, beam.isocenterPosition)
        coordGridX, coordGridY = self._pixelCoordinatedWrtIsocenter(cumRSPBEV, beam.isocenterPosition)

        spotGridX = spotGridX.flatten()
        spotGridY = spotGridY.flatten()

        for l, energy in enumerate(energyLayers):
            if energy<=0.:
                continue
            elif energy==energyLayers[0]:
                layerMask = weplMeV <= energy
            elif energy==energyLayers[-1]:
                layerMask = weplMeV > energy
            else:
                layerMask = np.logical_and(weplMeV>energy, weplMeV<=energyLayers[l+1])

            layerMask = np.sum(layerMask, axis=2).astype(bool)

            layerMask = np.logical_and(layerMask, np.sum(roiDilated.imageArray, axis=2).astype(bool))

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

    def _defineHexagSpotGridAroundIsocenter(self, spotSpacing: float, imageBEV: Image3D, isocenterBEV: Sequence[float]):
        origin = imageBEV.origin
        end = imageBEV.origin + imageBEV.spacing * imageBEV.imageArray.shape

        spotGridSpacing = [spotSpacing / 2., spotSpacing * cos(pi / 6.)]

        xFromIsoToOrigin = np.arange(isocenterBEV[0], origin[0], -spotGridSpacing[0])
        xFromOriginToIso = np.flipud(xFromIsoToOrigin)
        xFromIsoToEnd = np.arange(isocenterBEV[0] + spotGridSpacing[0], end[0], spotGridSpacing[0])
        yFromIsoToOrigin = np.arange(isocenterBEV[1], origin[1], -spotGridSpacing[1])
        yFromOriginToIso = np.flipud(yFromIsoToOrigin)
        yFromIsoToEnd = np.arange(isocenterBEV[1] + spotGridSpacing[1], end[1], spotGridSpacing[1])

        x = np.concatenate((xFromOriginToIso, xFromIsoToEnd))
        y = np.concatenate((yFromOriginToIso, yFromIsoToEnd))

        spotGridX, spotGridY = np.meshgrid(x, y)

        spotGridX = spotGridX - isocenterBEV[0]
        spotGridY = spotGridY - isocenterBEV[1]

        isoInd0 = xFromOriginToIso.shape[0]  # index of isocenter
        isoInd1 = yFromOriginToIso.shape[0]  # index of isocenter

        heaxagonalMask = np.zeros(spotGridX.shape)
        heaxagonalMask[(isoInd0 + 1) % 2::2, (isoInd1 + 1) % 2:2] = 1
        heaxagonalMask[1 - (isoInd0 + 1) % 2::2, 1 - (isoInd1 + 1) % 2::2] = 1

        spotGridX = spotGridX[heaxagonalMask.astype(bool)]
        spotGridY = spotGridY[heaxagonalMask.astype(bool)]

        return spotGridX, spotGridY

    def _pixelCoordinatedWrtIsocenter(self, imageBEV: Image3D, isocenterBEV: Sequence[float]):
        origin = imageBEV.origin
        end = imageBEV.origin + imageBEV.spacing * imageBEV.imageArray.shape

        x = np.arange(origin[0], end[0], imageBEV.spacing[0])
        y = np.arange(origin[1], end[1], imageBEV.spacing[1])
        [coordGridX, coordGridY] = np.meshgrid(x, y)
        coordGridX = np.transpose(coordGridX)
        coordGridY = np.transpose(coordGridY)

        coordGridX = coordGridX - isocenterBEV[0]
        coordGridY = coordGridY - isocenterBEV[1]

        return coordGridX, coordGridY


class PlanInitializer:
    def __init__(self):
        self.ctCalibration:AbstractCTCalibration=None
        self.ct:CTImage=None
        self.plan:RTPlan=None
        self.targetMask:ROIMask=None

        self._beamInitializer = BeamInitializerBEV()

    def initializePlan(self, spotSpacing:float, layerSpacing:float, targetMargin:float=0.):
        #TODO Range shifter


        self._beamInitializer.calibration = self.ctCalibration
        self._beamInitializer.spotSpacing = spotSpacing
        self._beamInitializer.layerSpacing = layerSpacing
        self._beamInitializer.targetMargin = targetMargin

        for beam in self.plan:
            beam.removeLayer(beam.layers)

            self._beamInitializer.beam = beam
            ctBEV = imageTransform3D.dicomToIECGantry(self.ct, beam, fillValue=0.,
                                                                      cropROI=self.targetMask, cropDim0=True,
                                                                      cropDim1=True, cropDim2=False)
            roiBEV = imageTransform3D.dicomToIECGantry(self.targetMask, beam, fillValue=0.,
                                                                      cropROI=self.targetMask, cropDim0=True,
                                                                      cropDim1=True, cropDim2=False)
            self._beamInitializer.intializeBeam(beam, ctBEV, roiBEV)
