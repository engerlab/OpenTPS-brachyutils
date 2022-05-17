import copy
import logging
import math
from typing import Optional, Tuple

import numpy as np

from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.image2D import Image2D
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.planIonBeam import PlanIonBeam
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Extensions.FLASH.Core.Data.abstractCTObject import AbstractCTObject
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam


logger = logging.getLogger(__name__)


class CEM(AbstractCTObject, Image2D):
    def __init__(self):
        Image2D.__init__(self)

        self.rsp:float = 1.

        self._referenceImage = None
        self._referenceImageBEV = None # _referenceImage in BEV. Nice to have it cached since computing BEV is not neglectible
        self._referenceBeam = None
        self._targetMask = None

    @classmethod
    def fromBeam(cls, ct:Image3D, beam:PlanIonBeam, targetMask=None):
        imageBEV = imageTransform3D.dicomToIECGantry(ct, beam, cropROI=targetMask, cropDim0=True, cropDim1=True, cropDim2=False)

        newCEM = cls()
        newCEM._referenceImage = CTImage.fromImage3D(ct)
        newCEM._referenceImageBEV = imageBEV
        newCEM._referenceBeam = beam
        newCEM.origin = imageBEV.origin[0:-1]
        newCEM.spacing = imageBEV.spacing[0:-1]
        newCEM.imageArray = np.zeros(imageBEV.gridSize[0:-1])

        newCEM._targetMask = targetMask

        return newCEM

    @property
    def targetMask(self) -> ROIMask:
        return self._targetMask

    @property
    def referenceBeam(self):
        return self._referenceBeam

    def computeBoundingBox(self) -> ROIMask:
        beam = self._referenceBeam
        referenceImageBEV = Image3D.fromImage3D(self._referenceImageBEV)
        referenceImage = self._referenceImage

        referenceImageBEV.origin = (self.origin[0], self.origin[1], referenceImageBEV.origin[2])
        data = np.zeros((self.imageArray.shape[0], self.imageArray.shape[1], referenceImageBEV.imageArray.shape[2]))
        referenceImageBEV.imageArray = data

        cemPixelsInDim2 = self._cemPixelsInDim2(referenceImage, referenceImageBEV, beam)
        availableSpaceInPixels = self._availableSpaceInPixels()

        cemPixelsInDim2 = cemPixelsInDim2.max()
        data[:, :, availableSpaceInPixels-cemPixelsInDim2:availableSpaceInPixels] = 1

        roiBEV = ROIMask.fromImage3D(referenceImageBEV)
        roiBEV.imageArray = data
        cropROI = ROIMask.fromImage3D(referenceImage)
        cropROI.imageArray = np.ones(cropROI.imageArray.shape).astype(bool)
        roi = imageTransform3D.iecGantryToDicom(roiBEV, beam)

        imageTransform3D.intersect(roi, referenceImage, inPlace=True, fillValue=0)

        imageArray = roi.imageArray
        imageArray[imageArray <= 0.5] = 0
        roi.imageArray = imageArray.astype(bool)

        return roi

    def computeROI(self) -> ROIMask:
        beam = self._referenceBeam
        referenceImageBEV = Image3D.fromImage3D(self._referenceImageBEV)
        referenceImage = self._referenceImage

        referenceImageBEV.origin = (self.origin[0], self.origin[1], referenceImageBEV.origin[2])
        data = np.zeros((self.imageArray.shape[0], self.imageArray.shape[1], referenceImageBEV.imageArray.shape[2]))
        referenceImageBEV.imageArray = data

        cemPixelsInDim2 = self._cemPixelsInDim2(referenceImage, referenceImageBEV, beam)
        availableSpaceInPixels = self._availableSpaceInPixels()

        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                if cemPixelsInDim2[i, j]>0:
                    data[i, j, availableSpaceInPixels - cemPixelsInDim2[i, j]:availableSpaceInPixels] = 1

        roiBEV = ROIMask.fromImage3D(referenceImageBEV)
        roiBEV.imageArray = data
        cropROI = ROIMask.fromImage3D(referenceImage)
        cropROI.imageArray = np.ones(cropROI.imageArray.shape).astype(bool)
        roi = imageTransform3D.iecGantryToDicom(roiBEV, beam)

        imageTransform3D.intersect(roi, referenceImage, inPlace=True, fillValue=0)

        imageArray = roi.imageArray
        imageArray[imageArray<=0.5] = 0
        roi.imageArray = imageArray.astype(bool)

        return roi

    def _cemPixelsInDim2(self, referenceImage, referenceImageBEV, beam):
        cemArray = self.imageArray

        cemPixelsInDim2 = np.round(cemArray / (self.rsp*referenceImageBEV.spacing[2]))

        availableSpaceInPixels = self._availableSpaceInPixels()
        if np.any(cemPixelsInDim2 > availableSpaceInPixels):
            maxDiff = np.max(cemPixelsInDim2 - availableSpaceInPixels)
            logger.info("CEM is larger by " + str(maxDiff) + ' pixels than available space (' + str(availableSpaceInPixels) + ' pixels) - Cropping.')
            cemPixelsInDim2[cemPixelsInDim2 > availableSpaceInPixels] = availableSpaceInPixels

        return cemPixelsInDim2.astype(int)

    def _availableSpaceInPixels(self):
        isocenterInImage = imageTransform3D.dicomCoordinate2iecGantry(self._referenceImage, self._referenceBeam, self._referenceBeam.isocenterPosition)
        isocenterCoord = self._referenceImageBEV.getVoxelIndexFromPosition(isocenterInImage)

        distInPixels = np.ceil(self._referenceBeam.cemToIsocenter/self._referenceImageBEV.spacing[2])

        return int(isocenterCoord[2] - distInPixels)


class BiComponentCEM(CEM):
    def __init__(self):
        self.rangeShifterRSP = 1.
        self.cemRSP = 1.
        self.minCEMThickness = 5. # in physical mm not in water equivalent mm
        self.rangeShifterToCEM = 10. # Free space between CEM and RS

        self._simpleCEM = CEM()
        self._simpleCEM.rsp = 1.

        super().__init__()

    @property
    def imageArray(self) -> np.ndarray:
        return self._simpleCEM.imageArray

    @imageArray.setter
    def imageArray(self, imageArray:np.ndarray):
        self._simpleCEM.imageArray = imageArray

    @property
    def origin(self) -> np.ndarray:
        return self._simpleCEM.origin

    @property
    def spacing(self) -> np.ndarray:
        return self._simpleCEM.spacing

    @property
    def targetMask(self) -> ROIMask:
        return self._simpleCEM.targetMask

    @classmethod
    def fromBeam(cls, ct:Image3D, beam:PlanIonBeam, targetMask=None):
        newCEM = cls()
        newCEM._simpleCEM = CEM.fromBeam(ct, beam, targetMask=targetMask)

        return newCEM

    def computeROI(self) -> ROIMask:
        rsROI, cemROI = self.computeROIs()

        outROI = ROIMask.fromImage3D(rsROI)
        outROI.imageArray = np.logical_or(rsROI.imageArray, cemROI.imageArray)

        return outROI

    def computeROIs(self) -> Tuple[ROIMask, ROIMask]:
        simpleRS, simpleCEM = self.split()

        rsROI = simpleRS.computeROI()

        simpleCEM.referenceBeam.cemToIsocenter += self._rangeShifterWET() / self.rangeShifterRSP + self.rangeShifterToCEM
        cemROI = simpleCEM.computeROI()

        return rsROI, cemROI


    def split(self) -> Tuple[CEM, CEM]:
        rangeShifterWaterEquivThick = self._rangeShifterWET()

        simpleRS = copy.deepcopy(self._simpleCEM)
        simpleRS.imageArray = rangeShifterWaterEquivThick*np.ones(simpleRS.imageArray.shape)*np.array(self._simpleCEM.imageArray.astype(bool).astype(float))
        simpleRS.rsp = self.rangeShifterRSP

        simpleCEM = copy.deepcopy(self._simpleCEM)
        imageArray = np.array(self._simpleCEM.imageArray) - rangeShifterWaterEquivThick
        imageArray[imageArray<0] = 0
        simpleCEM.imageArray = imageArray
        simpleCEM.rsp = self.cemRSP

        return simpleRS, simpleCEM

    def _rangeShifterWET(self) -> float:
        cemData = self._simpleCEM.imageArray
        cemData = cemData[cemData > self.cemRSP*self.minCEMThickness]

        if len(cemData)==0:
            raise ValueError("CEM cannot contains only 0s")

        cemDataMin = np.min(cemData)

        rangeShifterWET = cemDataMin - self.minCEMThickness * self.cemRSP

        if rangeShifterWET<0.:
            rangeShifterWET = 0.

        return self._roundRangeShifterWETToPixels(rangeShifterWET, self._referenceImage, self.referenceBeam)

    def _roundRangeShifterWETToPixels(self, rangeShifterWET:float, referenceImage:Optional[Image3D]=None, beam:Optional[CEMBeam]=None) -> float:
        if not (referenceImage is None):
            referenceImageBEV = imageTransform3D.dicomToIECGantry(referenceImage, beam)
        else:
            referenceImageBEV = self._simpleCEM._referenceImageBEV

        pixelWET = self.rangeShifterRSP*referenceImageBEV.spacing[2]

        rangeShifterWET = math.floor(rangeShifterWET/pixelWET)*pixelWET

        return rangeShifterWET
