import copy
from math import pi, cos, sin
from typing import Sequence, Optional, Union

import numpy as np
from numpy import linalg

from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.roiContour import ROIContour

try:
    from Core.Processing.ImageProcessing import sitkImageProcessing, crop3D

    resize = sitkImageProcessing.resize
except:
    print('No module SimpleITK found')


def add(image:Image3D, imageToSubtrat:Image3D, inPlace:bool=False, fillValue:float=0.) -> Optional[Image3D]:
    raise NotImplementedError

def subtract(image:Image3D, imageToSubtrat:Image3D, inPlace:bool=False, fillValue:float=0.) -> Optional[Image3D]:
    raise NotImplementedError

def resampleOn(image:Image3D, fixedImage:Image3D, inPlace:bool=False, fillValue:float=0.) -> Optional[Image3D]:
    if not inPlace:
        image = image.__class__.fromImage3D(image)

    if not(image.hasSameGrid(fixedImage)):
        resize(image, fixedImage.spacing, newOrigin=fixedImage.origin, newShape=fixedImage.gridSize.astype(int), fillValue=fillValue)

    return image

def extendAll(images:Sequence[Image3D], inPlace=False, fillValue:float=0.) -> Sequence[Image3D]:
    newOrigin = np.array([np.Inf, np.Inf, np.Inf])
    newSpacing = np.array([np.Inf, np.Inf, np.Inf])
    newEnd = np.array([-np.Inf, -np.Inf, -np.Inf])

    for image in images:
        o = image.origin
        e = image.origin + image.gridSizeInWorldUnit
        s = image.spacing

        for i in range(3):
            if o[i]<newOrigin[i]:
                newOrigin[i] = o[i]
            if e[i]>newEnd[i]:
                newEnd[i] = e[i]
            if s[i]<newSpacing[i]:
                newSpacing[i] = s[i]

    outImages = []
    for image in images:
        if not inPlace:
            image = image.__class__.fromImage3D(image)

        resize(image, newSpacing, newOrigin=newOrigin, newShape=np.round((newEnd - newOrigin)/newSpacing).astype(int),
               fillValue=fillValue)

        outImages.append(image)

    return outImages


def dicomToIECGantry(image:Image3D, beam:PlanIonBeam, fillValue:float=0, cropROI:Optional[Union[ROIContour, ROIMask]]=None,
                     cropDim0=True, cropDim1=True, cropDim2=True) -> Image3D:
    cropROI = None # TEST !!!!
    tform = _forwardDicomToIECGantry(image, beam)

    tform = linalg.inv(tform)

    outImage = image.__class__.fromImage3D(image)

    outputBox = _cropBoxAfterTransform(image, tform, cropROI, cropDim0, cropDim1, cropDim2)

    sitkImageProcessing.applyTransform(outImage, tform, fillValue=fillValue, outputBox=outputBox)

    return outImage

def _cropBox(image, cropROI:Optional[Union[ROIContour, ROIMask]], cropDim0, cropDim1, cropDim2) -> Optional[Sequence[float]]:
    outputBox = None

    if not (cropROI is None):
        outputBox = sitkImageProcessing.extremePoints(cropROI)
        roiBox = crop3D.getBoxAroundROI(cropROI)
        if cropDim0:
            outputBox[0] = roiBox[0][0]
            outputBox[1] = roiBox[0][1]
        if cropDim1:
            outputBox[2] = roiBox[1][0]
            outputBox[3] = roiBox[1][1]
        if cropDim2:
            outputBox[4] = roiBox[2][0]
            outputBox[5] = roiBox[2][1]

    return outputBox

def _cropBoxAfterTransform(image, tform, cropROI:Optional[Union[ROIContour, ROIMask]], cropDim0, cropDim1, cropDim2) -> Optional[Sequence[float]]:
    outputBox = None

    if not (cropROI is None):
        outputBox = np.array(sitkImageProcessing.extremePointsAfterTransform(image, tform))
        cropROIBEV = ROIMask.fromImage3D(cropROI)
        sitkImageProcessing.applyTransform(cropROIBEV, tform, fillValue=0)
        cropROIBEV.imageArray = cropROIBEV.imageArray.astype(bool)
        roiBox = crop3D.getBoxAroundROI(cropROIBEV)
        if cropDim0:
            outputBox[0] = roiBox[0][0]
            outputBox[1] = roiBox[0][1]
        if cropDim1:
            outputBox[2] = roiBox[1][0]
            outputBox[3] = roiBox[1][1]
        if cropDim2:
            outputBox[4] = roiBox[2][0]
            outputBox[5] = roiBox[2][1]

    return outputBox

def dicomCoordinate2iecGantry(image:Image3D, beam:PlanIonBeam, point:Sequence[float]) -> Sequence[float]:
    u = point[0]
    v = point[1]
    w = point[2]

    tform = _forwardDicomToIECGantry(image, beam)
    tform = linalg.inv(tform)

    return sitkImageProcessing.applyTransformToPoint(tform, np.array((u, v, w)))

def iecGantryToDicom(image:Image3D, beam:PlanIonBeam, fillValue:float=0, cropROI:Optional[Union[ROIContour, ROIMask]]=None,
                     cropDim0=True, cropDim1=True, cropDim2=True) -> Image3D:
    cropROI = None  # TEST !!!!
    tform = _forwardDicomToIECGantry(image, beam)

    outputBox = _cropBox(image, cropROI, cropDim0, cropDim1, cropDim2)

    outImage = image.__class__.fromImage3D(image)
    sitkImageProcessing.applyTransform(outImage, tform, fillValue=fillValue, outputBox=outputBox)

    return outImage

def iecGantryCoordinatetoDicom(image: Image3D, beam: PlanIonBeam, point: Sequence[float]) -> Sequence[float]:
    u = point[0]
    v = point[1]
    w = point[2]

    tform = _forwardDicomToIECGantry(image, beam)

    return sitkImageProcessing.applyTransformToPoint(tform, np.array((u, v, w)))

def _forwardDicomToIECGantry(image:Image3D, beam:PlanIonBeam) -> np.ndarray:
    isocenter = beam.isocenterPosition
    gantryAngle = beam.gantryAngle
    patientSupportAngle = beam.patientSupportAngle

    orig = np.array(isocenter) - np.array(image.origin)

    M = _roll(-gantryAngle, [0, 0, 0]) @ \
        _rot(patientSupportAngle, [0, 0, 0]) @ \
        _pitch(-90, [0, 0, 0])

    Trs = [[1., 0., 0., -orig[0]],
           [0., 1., 0., -orig[1]],
           [0., 0., 1., -orig[2]],
           [0., 0., 0., 1.]]

    Flip = [[1., 0., 0., 0.],
            [0., 1., 0., 0.],
            [0., 0., -1., 0.],
            [0., 0., 0., 1.]]

    Trs = np.array(Trs)
    Flip = np.array(Flip)

    T = linalg.inv(Flip @ Trs) @ M @ Flip @ Trs

    return T

def _roll(angle:float, offset:Sequence[float]) -> np.ndarray:
    a = pi * angle / 180.
    ca = cos(a)
    sa = sin(a)

    R = [[ca, 0., sa, offset[0]],
         [0., 1., 0., offset[1]],
         [-sa, 0., ca, offset[2]],
         [0., 0., 0., 1.]]

    return np.array(R)

def _rot(angle:float, offset:Sequence[float]) -> np.ndarray:
    a = pi * angle / 180.
    ca = cos(a)
    sa = sin(a)

    R = [[ca, -sa, 0., offset[0]],
         [sa, ca, 0., offset[1]],
         [0., 0., 1., offset[2]],
         [0., 0., 0., 1.]]

    return np.array(R)

def _pitch(angle:float, offset:Sequence[float]) -> np.ndarray:
    a = pi * angle / 180.
    ca = cos(a)
    sa = sin(a)

    R = [[1., 0., 0., offset[0]],
         [0., ca, -sa, offset[1]],
         [0., sa, ca, offset[2]],
         [0., 0., 0., 1.]]

    return np.array(R)
