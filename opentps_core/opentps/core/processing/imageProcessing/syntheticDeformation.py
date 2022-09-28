import numpy as np
import logging

from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data._roiContour import ROIContour
from opentps.core.data.images._deformation3D import Deformation3D
from opentps.core.data.dynamicData.dynamic3DModel import Dynamic3DModel
import opentps.core.processing.imageProcessing.filter3D as imageFilter3D
from opentps.core.processing.imageProcessing import resampler3D
from opentps.core.processing.segmentation.segmentationCT import compute3DStructuralElement

logger = logging.getLogger(__name__)


def applyBaselineShift(inputData, ROI, shift, sigma=2, tryGPU=True):

    if not np.array(shift == np.array([0, 0, 0])).all(): ## check if there is a shift to apply

        if isinstance(inputData, Dynamic3DModel):
            model = inputData.copy()
            image = inputData.midp
        else:
            image = inputData

        if isinstance(ROI, ROIContour):
            mask = ROI.getBinaryMask(origin=image.origin, gridSize=image.gridSize, spacing=image.spacing)
        elif isinstance(ROI, ROIMask):
            mask = ROI

        maskMoving = mask.copy()
        maskMoving.dilate(filt=compute3DStructuralElement([sigma, sigma, sigma], spacing=maskMoving.spacing))

        maskFixed = maskMoving.copy()
        for i in range(3):
            maskFixed.origin[i] += shift[i]
        resampler3D.resampleImage3DOnImage3D(maskFixed, image, inPlace=True, fillValue=0)
        maskFixed._imageArray = np.logical_or(maskFixed.imageArray, maskMoving.imageArray)

        deformation = Deformation3D()
        deformation.initFromImage(image)

        cert = maskFixed.copy()
        cert._imageArray = maskFixed.imageArray.astype(np.float32)/1.1 + 0.1
        cert._imageArray[image.imageArray > 200] = 100

        for i in range(3):
            deformation = forceShiftInMask(deformation, maskFixed, shift)
            deformation.setVelocityArrayXYZ(
                imageFilter3D.normGaussConv(deformation.velocity.imageArray[:, :, :, 0], cert.imageArray, sigma, tryGPU=tryGPU),
                imageFilter3D.normGaussConv(deformation.velocity.imageArray[:, :, :, 1], cert.imageArray, sigma, tryGPU=tryGPU),
                imageFilter3D.normGaussConv(deformation.velocity.imageArray[:, :, :, 2], cert.imageArray, sigma, tryGPU=tryGPU))

        if isinstance(inputData, Dynamic3DModel):
            for i in range(len(model.deformationList)):
                model.deformationList[i].setVelocity(deformation.deformImage(inputData.deformationList[i].velocity, fillValue='closest', tryGPU=tryGPU))
            model.midp = deformation.deformImage(image, fillValue='closest', tryGPU=tryGPU)
            return model, deformation.deformImage(mask, fillValue='closest', tryGPU=tryGPU)
        else:
            return deformation.deformImage(image, fillValue='closest', tryGPU=tryGPU), deformation.deformImage(mask, fillValue='closest', tryGPU=tryGPU)
    else:
        if isinstance(inputData, Dynamic3DModel):
            return inputData, ROI
        else:
            return ROI


def forceShiftInMask(deformation,mask,shift):

    for i in range(3):
        temp = deformation.velocity.imageArray[:, :, :, i]
        temp[mask.imageArray.nonzero()] = -shift[i]
        deformation.velocity._imageArray[:, :, :, i] = temp

    return deformation
