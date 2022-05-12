import numpy as np
import logging

from Core.Data.Images.roiMask import ROIMask
from Core.Data.roiContour import ROIContour
from Core.Data.Images.deformation3D import Deformation3D
import Core.Processing.ImageProcessing.imageFilter3D as imageFilter3D
from Core.Processing.Segmentation.segmentationCT import compute3DStructuralElement

logger = logging.getLogger(__name__)


def applyBaselineShift(image, ROI, shift, sigma=2):

    if isinstance(ROI, ROIContour):
        maskMoving = ROI.getBinaryMask()
    elif isinstance(ROI, ROIMask):
        maskMoving = ROI

    maskMoving = maskMoving.copy()
    maskMoving.dilate(filt=compute3DStructuralElement([sigma, sigma, sigma], spacing=maskMoving.spacing))

    maskFixed = maskMoving.copy()
    for i in range(3):
        maskFixed.origin[i] += shift[i]
    maskFixed.resampleToImageGrid(image)
    maskFixed._imageArray = np.logical_or(maskFixed.imageArray, maskMoving.imageArray)

    deformation = Deformation3D()
    deformation.initFromImage(image)

    cert = maskFixed.copy()
    cert._imageArray = maskFixed.imageArray.astype(np.float32)/1.1 + 0.1
    cert._imageArray[image.imageArray > 200] = 100

    for i in range(3):
        deformation = forceShiftInMask(deformation, maskFixed, shift)
        deformation.setVelocityArrayXYZ(
            imageFilter3D.normGaussConv(deformation.velocity.imageArray[:, :, :, 0], cert.imageArray, sigma),
            imageFilter3D.normGaussConv(deformation.velocity.imageArray[:, :, :, 1], cert.imageArray, sigma),
            imageFilter3D.normGaussConv(deformation.velocity.imageArray[:, :, :, 2], cert.imageArray, sigma))

    return deformation.deformImage(image, fillValue='closest')


def forceShiftInMask(deformation,mask,shift):

    for i in range(3):
        temp = deformation.velocity.imageArray[:, :, :, i]
        temp[mask.imageArray.nonzero()] = -shift[i]
        deformation.velocity._imageArray[:, :, :, i] = temp

    return deformation