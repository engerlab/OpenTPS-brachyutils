
import logging

import numpy as np

from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.image2D import Image2D
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.planIonBeam import PlanIonBeam
import Core.Processing.ImageProcessing.imageTransform3D as imageTransform3D
from Extensions.FLASH.Core.Data.abstractCTObject import AbstractCTObject


logger = logging.getLogger(__name__)

class Aperture(AbstractCTObject, Image2D):
    def __init__(self):
        Image2D.__init__(self)

        self.rsp:float = 1.
        self.wet:float = 100.

        self._referenceImage = None
        self._referenceImageBEV = None # _referenceImage in BEV. Nice to have it cached since computing BEV is not neglectible
        self._referenceBeam = None
        self._targetMask = None
        self._cropROI = None

    @classmethod
    def fromBeam(cls, ct:Image3D, beam:PlanIonBeam, targetMask:ROIMask, clearance:float=0., lateralThickness:float=10.):
        newCEM = cls()

        targetMaskDilated = ROIMask.fromImage3D(targetMask)
        print(lateralThickness+clearance+ct.spacing.max())
        targetMaskDilated.dilate(lateralThickness+clearance+ct.spacing.max()) # ct.spacing.max() is just a margin
        print('dilated')
        newCEM._cropROI = targetMaskDilated

        targetMaskWithClearance = ROIMask.fromImage3D(targetMask)
        if clearance>0:
            targetMaskWithClearance.dilate(clearance)

        imageBEV = imageTransform3D.dicomToIECGantry(ct, beam, cropROI=newCEM._cropROI, cropDim0=True, cropDim1=True, cropDim2=False)
        roiBEV = imageTransform3D.dicomToIECGantry(targetMaskWithClearance, beam, cropROI=newCEM._cropROI, cropDim0=True, cropDim1=True,
                                                     cropDim2=False)

        apertureROI = np.logical_not(roiBEV.imageArray.sum(axis=2).astype(bool))

        newCEM._referenceImage = CTImage.fromImage3D(ct)
        newCEM._referenceImageBEV = imageBEV
        newCEM._referenceBeam = beam
        newCEM._targetMask = targetMask
        newCEM.origin = imageBEV.origin[0:-1]
        newCEM.spacing = imageBEV.spacing[0:-1]
        newCEM.imageArray = apertureROI

        return newCEM

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
        cemArray = self.imageArray.astype(float)*self.wet

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

        distInPixels = np.ceil(self._referenceBeam.apertureToIsocenter /self._referenceImageBEV.spacing[2])

        return int(isocenterCoord[2] - distInPixels)
