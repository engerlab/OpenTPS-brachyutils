import copy
import logging
import math
from typing import Optional, Tuple

import numpy as np
from scipy.interpolate import interpolate

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

    @classmethod
    def fromBeam(cls, ct:Image3D, beam:PlanIonBeam):
        imageBEV = imageTransform3D.dicomToIECGantry(ct, beam)

        newCEM = cls()
        newCEM._referenceImage = CTImage.fromImage3D(ct)
        newCEM._referenceImageBEV = imageBEV
        newCEM._referenceBeam = beam
        newCEM.origin = imageBEV.origin[0:-1]
        newCEM.spacing = imageBEV.spacing[0:-1]
        newCEM.imageArray = np.zeros(imageBEV.gridSize[0:-1])

        return newCEM

    @property
    def referenceBeam(self):
        return self._referenceBeam

    def computeROI(self, referenceImage:Image3D, beam:Optional[CEMBeam]=None) -> ROIMask:
        if beam is None:
            beam = self._referenceBeam

        referenceImageBEV = imageTransform3D.dicomToIECGantry(referenceImage, beam)

        data = np.zeros(referenceImageBEV.imageArray.shape)

        cemPixelsInDim2 = self._cemPixelsInDim2(referenceImage, referenceImageBEV, beam)
        availableSpaceInPixels = self._availableSpaceInPixels(referenceImage, referenceImageBEV, beam)

        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                if cemPixelsInDim2[i, j]>0:
                    data[i, j, availableSpaceInPixels - cemPixelsInDim2[i, j]:availableSpaceInPixels] = 1

        roiBEV = ROIMask.fromImage3D(referenceImageBEV)
        roiBEV.imageArray = data
        roi = imageTransform3D.iecGantryToDicom(roiBEV, beam)
        imageTransform3D.intersect(roi, referenceImage, inPlace=True, fillValue=0)
        imageArray = roi.imageArray
        imageArray[imageArray<=0.5] = 0
        roi.imageArray = imageArray.astype(bool)

        return roi

    def _cemPixelsInDim2(self, referenceImage, referenceImageBEV, beam):
        cemArray = self._resampleCEMArray(referenceImageBEV)

        cemPixelsInDim2 = np.round(cemArray / (self.rsp*referenceImageBEV.spacing[2]))

        availableSpaceInPixels = self._availableSpaceInPixels(referenceImage, referenceImageBEV, beam)
        if np.any(cemPixelsInDim2 > availableSpaceInPixels):
            maxDiff = np.max(cemPixelsInDim2 - availableSpaceInPixels)
            logger.info("CEM is larger by " + str(maxDiff) + ' pixels than available space (' + str(availableSpaceInPixels) + ' pixels) - Cropping.')
            cemPixelsInDim2[cemPixelsInDim2 > availableSpaceInPixels] = availableSpaceInPixels

        return cemPixelsInDim2.astype(int)

    def _availableSpaceInPixels(self, referenceImage, referenceImageBEV, beam):
        isocenterInImage = imageTransform3D.dicomCoordinate2iecGantry(referenceImage, beam, beam.isocenterPosition)
        isocenterCoord = referenceImageBEV.getVoxelIndexFromPosition(isocenterInImage)

        distInPixels = np.ceil(beam.cemToIsocenter / referenceImageBEV.spacing[2])

        return int(isocenterCoord[2] - distInPixels)
    
    def _resampleCEMArray(self, referenceImageBEV:Image3D) -> np.ndarray:
        if self._hasSameSpatialReferencing(referenceImageBEV):
            return self.imageArray

        x = np.arange(self.origin[0], self.gridSizeInWorldUnit[0], self.spacing[0])
        y = np.arange(self.origin[1], self.gridSizeInWorldUnit[1], self.spacing[1])

        f = interpolate.interp2d(x, y, self.imageArray, kind='linear')

        x2 = np.arange(referenceImageBEV.origin[0], referenceImageBEV.gridSizeInWorldUnit[0], referenceImageBEV.spacing[0])
        y2 = np.arange(referenceImageBEV.origin[1], referenceImageBEV.gridSizeInWorldUnit[1], referenceImageBEV.spacing[1])

        xx, yy = np.meshgrid(x2, y2)

        return f(xx, yy)

    def _hasSameSpatialReferencing(self, other):
        if not(math.isclose(self.origin[0], other.origin[0], abs_tol=0.0001)) or \
                not(math.isclose(self.origin[1], other.origin[1], abs_tol=0.0001)):
            return False

        if not (math.isclose(self.spacing[0], other.spacing[0], abs_tol=0.0001)) or \
                not (math.isclose(self.spacing[1], other.spacing[1], abs_tol=0.0001)):
            return False

        if not (math.isclose(self.gridSizeInWorldUnit[0], other.gridSizeInWorldUnit[0], abs_tol=0.0001)) or \
                not (math.isclose(self.gridSizeInWorldUnit[1], other.gridSizeInWorldUnit[1], abs_tol=0.0001)):
            return False

        return True


class BiComponentCEM(AbstractCTObject):
    def __init__(self):
        super().__init__()

        self.rangeShifterRSP = 1.
        self.cemRSP = 1.
        self.minCEMThickness = 5. # in physical mm not in water equivalent mm
        self.rangeShifterToCEM = 10. # Free space between CEM and RS

        self._simpleCEM = CEM()
        self._simpleCEM.rsp = 1.

    @property
    def imageArray(self) -> np.ndarray:
        return self._simpleCEM.imageArray

    @imageArray.setter
    def imageArray(self, imageArray:np.ndarray):
        self._simpleCEM.imageArray = imageArray

    @property
    def origin(self) -> np.ndarray:
        return self._simpleCEM.origin

    @origin.setter
    def origin(self, origin: np.ndarray):
        self._simpleCEM.origin = origin

    @property
    def spacing(self) -> np.ndarray:
        return self._simpleCEM.spacing

    @spacing.setter
    def spacing(self, spacing: np.ndarray):
        self._simpleCEM.spacing = spacing

    @classmethod
    def fromBeam(cls, ct:Image3D, beam:PlanIonBeam):
        newCEM = cls()
        newCEM._simpleCEM = CEM.fromBeam(ct, beam)

        return newCEM

    def computeROI(self, referenceImage:Image3D, beam:Optional[CEMBeam]=None) -> ROIMask:
        rsROI, cemROI = self.computeROIs(referenceImage, beam)

        outROI = ROIMask.fromImage3D(rsROI)
        outROI.imageArray = np.logical_or(rsROI.imageArray, cemROI.imageArray)

        return outROI


    def computeROIs(self, referenceImage:Image3D, beam:Optional[CEMBeam]=None) -> Tuple[ROIMask, ROIMask]:
        simpleRS, simpleCEM = self.split(referenceImage, beam)

        rsROI = simpleRS.computeROI(referenceImage, beam)

        beamCEM = copy.deepcopy(beam)
        beamCEM.cemToIsocenter += self._rangeShifterWET(referenceImage, beam) / self.rangeShifterRSP + self.rangeShifterToCEM

        cemROI = simpleCEM.computeROI(referenceImage, beamCEM)

        return rsROI, cemROI


    def split(self, referenceImage:Image3D, beam:Optional[CEMBeam]=None) -> Tuple[CEM, CEM]:
        rangeShifterWaterEquivThick = self._rangeShifterWET(referenceImage, beam)

        simpleRS = copy.deepcopy(self._simpleCEM)
        simpleRS.imageArray = rangeShifterWaterEquivThick*np.ones(simpleRS.imageArray.shape)*np.array(self._simpleCEM.imageArray.astype(bool).astype(float))
        simpleRS.rsp = self.rangeShifterRSP

        simpleCEM = copy.deepcopy(self._simpleCEM)
        imageArray = np.array(self._simpleCEM.imageArray) - rangeShifterWaterEquivThick
        imageArray[imageArray<0] = 0
        simpleCEM.imageArray = imageArray
        simpleCEM.rsp = self.cemRSP

        return simpleRS, simpleCEM

    def _rangeShifterWET(self, referenceImage:Image3D, beam:Optional[CEMBeam]=None) -> float:
        cemData = self._simpleCEM.imageArray
        cemData = cemData[cemData > self.cemRSP*self.minCEMThickness]

        if len(cemData)==0:
            raise ValueError("CEM cannot contains only 0s")

        cemDataMin = np.min(cemData)

        rangeShifterWET = cemDataMin - self.minCEMThickness * self.cemRSP

        if rangeShifterWET<0.:
            rangeShifterWET = 0.

        return self._roundRangeShifterWETToPixels(rangeShifterWET, referenceImage, beam)

    def _roundRangeShifterWETToPixels(self, rangeShifterWET:float, referenceImage:Image3D, beam:Optional[CEMBeam]=None) -> float:
        referenceImageBEV = imageTransform3D.dicomToIECGantry(referenceImage, beam)

        pixelWET = self.rangeShifterRSP*referenceImageBEV.spacing[2]

        rangeShifterWET = math.floor(rangeShifterWET/pixelWET)*pixelWET

        return rangeShifterWET
