from math import cos, pi
from typing import Sequence

import numpy as np
import pydicom

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Images.rspImage import RSPImage
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer

import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Extensions.FLASH.Core.Processing.RangeEnergy import rangeToEnergy


class PlanStructure:
    def __init__(self):
        self.spotSpacing = 5.0
        self.layerSpacing = 5.0
        self.targetMargin = 5.0
        self.targetMask: ROIMask = None
        self.proximalLayers = 1
        self.distalLayers = 1
        self.alignLayersToSpacing = False
        self.calibration: AbstractCTCalibration = None
        self.ct: CTImage = None
        self.beamNames = []
        self.gantryAngles = []
        self.couchAngles = []


    def createPlan(self):
        from Core.Data.Plan.rtPlan import RTPlan
        plan = RTPlan()
        plan.planDesign = self
        plan.SOPInstanceUID = pydicom.uid.generate_uid()
        plan.seriesInstanceUID = plan.SOPInstanceUID + ".1"
        plan.planName = "newPlan"
        plan.modality = "Ion therapy"
        plan.radiationType = "Proton"
        plan.scanMode = "MODULATED"
        plan.treatmentMachineName = "Unknown"
        plan.numberOfFractionsPlanned = 1

        roiDilated = ROIMask.fromImage3D(self.targetMask)
        roiDilated.dilate(radius=self.targetMargin)

        rspImage = RSPImage.fromCT(self.ct, self.calibration, energy=100.)

        # initialize each beam
        for b in range(len(self.gantryAngles)):
            plan.appendBeam(PlanIonBeam())
            plan.beams[b].name = self.beamNames[b]
            plan.beams[b].gantryAngle = self.gantryAngles[b]
            plan.beams[b].couchAngle = self.couchAngles[b]
            plan.beams[b].isocenterPosition = isoCenter

            self._intializeBeam(plan.beams[b], rspImage, roiDilated, self.spotSpacing, self.layerSpacing)

        return plan


    def _intializeBeam(self, beam: PlanIonBeam, rspImage: RSPImage, targetROI: ROIMask, spotSpacing: float,
                       layerSpacing: float):
        beam.isocenterPosition = targetROI.centerOfMass

        cumRSP = rspImage.computeCumulativeWEPL(beam)
        imageArray = np.array(cumRSP.imageArray)
        imageArray[np.logical_not(targetROI.imageArray.astype(bool))] = 0
        cumRSP.imageArray = imageArray

        maxWEPL = cumRSP.imageArray.max()
        minWEPL = cumRSP.imageArray[cumRSP.imageArray > 0.].min()

        rangeLayers = np.arange(minWEPL - layerSpacing, maxWEPL + layerSpacing, layerSpacing)
        energyLayers = rangeToEnergy(rangeLayers)

        targetROIBEV = imageTransform3D.dicomToIECGantry(targetROI, beam, fillValue=0., cropROI=targetROI,
                                                         cropDim0=True, cropDim1=True, cropDim2=False)
        isocenterBEV = imageTransform3D.dicomCoordinate2iecGantry(rspImage, beam, beam.isocenterPosition)
        cumRSPBEV = imageTransform3D.dicomToIECGantry(cumRSP, beam, fillValue=0., cropROI=targetROI, cropDim0=True,
                                                      cropDim1=True, cropDim2=False)
        weplMeV = rangeToEnergy(cumRSPBEV.imageArray)

        spotGridX, spotGridY = self._defineHexagSpotGridAroundIsocenter(spotSpacing, cumRSPBEV, isocenterBEV)
        coordGridX, coordGridY = self._pixelCoordinatedWrtIsocenter(cumRSPBEV, isocenterBEV)

        spotGridX = spotGridX.flatten()
        spotGridY = spotGridY.flatten()

        for l, energy in enumerate(energyLayers):
            if energy <= 0.:
                continue
            elif energy == energyLayers[0]:
                layerMask = weplMeV <= energy
            elif energy == energyLayers[-1]:
                layerMask = weplMeV > energy
            else:
                layerMask = np.logical_and(weplMeV > energy, weplMeV <= energyLayers[l + 1])

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

            ind = (x2 * x2 + y2 * y2).argmin(axis=0)

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

