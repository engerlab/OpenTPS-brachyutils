import copy
from math import pi, cos, sin
from typing import Sequence, Optional

import numpy as np
from numpy import linalg

from Core.Data.Images.image3D import Image3D
from Core.Data.Plan.planIonBeam import PlanIonBeam
try:
    from Core.Processing.ImageProcessing import sitkImageProcessing
except:
    print('No module SimpleITK found')


resize = sitkImageProcessing.resize

def intersect(image:Image3D, fixedImage:Image3D, inPlace:bool=False, fillValue:float=0.) -> Optional[Image3D]:
    if not inPlace:
        image = image.__class__.fromImage3D(image)

    resize(image, fixedImage.spacing, newOrigin=fixedImage.origin, newShape=fixedImage.gridSize.astype(int),
                               fillValue=fillValue)

    return image

def dicomToIECGantry(image:Image3D, beam:PlanIonBeam, fillValue:float=0) -> Image3D:
    tform = _forwardDicomToIECGantry(image, beam)

    tform = linalg.inv(tform)

    outImage = image.__class__.fromImage3D(image)
    sitkImageProcessing.applyTransform(outImage, tform, fillValue=fillValue)

    return outImage

def dicomCoordinate2iecGantry(image:Image3D, beam:PlanIonBeam, point:Sequence[float]) -> Sequence[float]:
    u = point[0]
    v = point[1]
    w = point[2]

    tform = _forwardDicomToIECGantry(image, beam)
    tform = linalg.inv(tform)

    return sitkImageProcessing.applyTransformToPoint(tform, np.array((u, v, w)))

def iecGantryToDicom(image:Image3D, beam:PlanIonBeam, fillValue:float=0) -> Image3D:
    tform = _forwardDicomToIECGantry(image, beam)

    #tform = linalg.inv(tform)

    outImage = image.__class__.fromImage3D(image)
    sitkImageProcessing.applyTransform(outImage, tform, fillValue=fillValue)

    return outImage

def iecGantryCoordinatetoDicom(image: Image3D, beam: PlanIonBeam, point: Sequence[float]) -> Sequence[float]:
    u = point[0]
    v = point[1]
    w = point[2]

    tform = _forwardDicomToIECGantry(image, beam)
    #tform = linalg.inv(tform)

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

    #T = np.transpose(T)

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
