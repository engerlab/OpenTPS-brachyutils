from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union, Sequence

if TYPE_CHECKING:
    from opentps.core.data.images import ROIMask, Image3D

import logging
from math import pi, cos, sin
from typing import Sequence, Optional, Union

import numpy as np
from numpy import linalg
from scipy.spatial.transform import Rotation as R
import copy

from opentps.core.data.images._image3D import Image3D
from opentps.core.data.plan._planIonBeam import PlanIonBeam
# from opentps.core.data._roiContour import ROIContour
# from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images._vectorField3D import VectorField3D

from opentps.core.data._roiContour import ROIContour
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.processing.segmentation import segmentation3D
from opentps.core.processing.imageProcessing import sitkImageProcessing, cupyImageProcessing





logger = logging.getLogger(__name__)

try:
    from opentps.core.processing.imageProcessing import sitkImageProcessing
except:
    logger.warning('No module SimpleITK found')


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
            image = image.__class__.fromImage3D(image, patient=None)

        sitkImageProcessing.resize(image, newSpacing, newOrigin=newOrigin, newShape=np.round((newEnd - newOrigin) / newSpacing).astype(int),
                                   fillValue=fillValue)

        outImages.append(image)

    return outImages


def dicomToIECGantry(image:Image3D, beam:PlanIonBeam, fillValue:float=0, cropROI:Optional[Union[ROIContour, ROIMask]]=None,
                     cropDim0=True, cropDim1=True, cropDim2=True) -> Image3D:
    logger.info("Resampling image DICOM -> IEC Gantry")

    tform = _forwardDicomToIECGantry(beam)

    tform = linalg.inv(tform)

    outImage = image.__class__.fromImage3D(image, patient=None)

    outputBox = _cropBoxAfterTransform(image, tform, cropROI, cropDim0, cropDim1, cropDim2)

    sitkImageProcessing.applyTransform3D(outImage, tform, fillValue=fillValue, outputBox=outputBox)

    return outImage

def _cropBox(image, cropROI:Optional[Union[ROIContour, ROIMask]], cropDim0, cropDim1, cropDim2) -> Optional[Sequence[float]]:
    outputBox = "keepAll"

    if not (cropROI is None):
        outputBox = sitkImageProcessing.extremePoints(cropROI)
        roiBox = segmentation3D.getBoxAroundROI(cropROI)
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
    outputBox = 'keepAll'

    if not (cropROI is None):
        from opentps.core.data.images._roiMask import ROIMask

        outputBox = np.array(sitkImageProcessing.extremePointsAfterTransform(image, tform))
        cropROIBEV = ROIMask.fromImage3D(cropROI, patient=None)
        sitkImageProcessing.applyTransform3D(cropROIBEV, tform, fillValue=0)
        cropROIBEV.imageArray = cropROIBEV.imageArray.astype(bool)
        roiBox = segmentation3D.getBoxAroundROI(cropROIBEV)
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

def dicomCoordinate2iecGantry(beam:PlanIonBeam, point:Sequence[float]) -> Sequence[float]:
    u = point[0]
    v = point[1]
    w = point[2]

    tform = _forwardDicomToIECGantry(beam)
    tform = linalg.inv(tform)

    return sitkImageProcessing.applyTransform3DToPoint(tform, np.array((u, v, w)))

def iecGantryToDicom(image:Image3D, beam:PlanIonBeam, fillValue:float=0, cropROI:Optional[Union[ROIContour, ROIMask]]=None,
                     cropDim0=True, cropDim1=True, cropDim2=True) -> Image3D:
    logger.info("Resampling image IEC Gantry -> DICOM")

    tform = _forwardDicomToIECGantry(beam)

    outputBox = _cropBox(image, cropROI, cropDim0, cropDim1, cropDim2)

    outImage = image.__class__.fromImage3D(image, patient = None)
    sitkImageProcessing.applyTransform3D(outImage, tform, fillValue=fillValue, outputBox=outputBox)

    return outImage

def iecGantryCoordinatetoDicom(beam: PlanIonBeam, point: Sequence[float]) -> Sequence[float]:
    u = point[0]
    v = point[1]
    w = point[2]

    tform = _forwardDicomToIECGantry(beam)

    return sitkImageProcessing.applyTransform3DToPoint(tform, np.array((u, v, w)))

def _forwardDicomToIECGantry(beam:PlanIonBeam) -> np.ndarray:
    isocenter = beam.isocenterPosition
    gantryAngle = beam.gantryAngle
    patientSupportAngle = beam.couchAngle

    orig = np.array(isocenter)

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


def getVoxelIndexFromPosition(position, image3D):
    """
    Get the voxel index of the position given in scanner coordinates.

    Parameters
    ----------
    position : tuple or list of 3 elements in scanner coordinates
        The 3D position that will be translated into voxel indexes
    image3D : Image3D
        The 3D image that contains its position in scanner coordinates and voxel spacing

    Returns
    -------
    posInVoxels : the 3D position as voxel indexes in the input image voxel grid
    """
    positionInMM = np.array(position)
    shiftedPosInMM = positionInMM - image3D.origin
    posInVoxels = np.round(np.divide(shiftedPosInMM, image3D.spacing)).astype(np.int)

    return posInVoxels


def transform3DMatrixFromTranslationAndRotationsVectors(transVec=[0, 0, 0], rotVec=[0, 0, 0]):

    """

    Parameters
    ----------
    transVec
    rotVec

    Returns
    -------

    """
    rotAngleInDeg = np.array(rotVec)
    rotAngleInRad = -rotAngleInDeg * np.pi / 180
    r = R.from_euler('XYZ', rotAngleInRad)

    affineTransformMatrix = np.array([[1, 0, 0, -transVec[0]],
                                  [0, 1, 0, -transVec[1]],
                                  [0, 0, 1, -transVec[2]],
                                  [0, 0, 0, 1]]).astype(np.float)

    affineTransformMatrix[0:3, 0:3] = r.as_matrix()

    return affineTransformMatrix


def getTtransformMatrixInPixels(transformMatrixInMM, spacing):

    transformMatrixInPixels = copy.copy(transformMatrixInMM)
    for i in range(3):
        transformMatrixInPixels[i, 3] = transformMatrixInPixels[i, 3] /spacing[i]

    return transformMatrixInPixels

def translateData(data, translationInMM, outputBox='keepAll', fillValue=-1000, tryGPU=False):

    if outputBox == 'keepAll':
        translateDataByChangingOrigin(data, translationInMM)
    else:
        if tryGPU:
            cupyImageProcessing.translateData(data, translationInMM=translationInMM, fillValue=fillValue, outputBox=outputBox)
        else:
            sitkImageProcessing.translateData(data, translationInMM=translationInMM, fillValue=fillValue, outputBox=outputBox)

def rotateData(data, rotAnglesInDeg, outputBox='keepAll', fillValue=-1000, rotCenter='imgCenter', tryGPU=False):

    if tryGPU:
        cupyImageProcessing.rotateData(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter)
    else:
        sitkImageProcessing.rotateData(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter)

def applyTransform3D(data, tformMatrix:np.ndarray, fillValue:float=-1000, outputBox:Optional[Union[Sequence[float], str]]='keepAll',
    rotCenter: Optional[Union[Sequence[float], str]]='dicomOrigin', translation:Sequence[float]=[0, 0, 0], tryGPU=False):

    if tryGPU:
        print(NotImplementedError)
    else:
        sitkImageProcessing.applyTransform3D(data, tformMatrix=tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter, translation=translation)


def parseRotCenter(rotCenterArg: Optional[Union[Sequence[float], str]], image: Image3D):
    rotCenter = np.array([0, 0, 0]).astype(float)

    if not (rotCenterArg is None):
        if rotCenterArg == 'dicomOrigin':
            rotCenter = np.array([0, 0, 0]).astype(float)
        # elif len(rotCenter) == 3 and (rotCenter[0].dtype == 'float64' or rotCenter[0].dtype == 'int'):
        elif len(rotCenterArg) == 3 and (isinstance(rotCenterArg[0], float) or isinstance(rotCenterArg[0], int)):
            rotCenter = rotCenterArg
        elif rotCenterArg == 'imgCorner':
            rotCenter = image.origin.astype(float)
        elif rotCenterArg == 'imgCenter':
            rotCenter = image.origin + image.gridSizeInWorldUnit / 2
        else:
            rotCenter = image.origin + image.gridSizeInWorldUnit / 2
            print('Rotation center not recognized, default value is used (image center)', type(rotCenter), rotCenter)

    return rotCenter


def translateDataByChangingOrigin(data, translationInMM):

    print('in imageTransform3D, translateDataByChangingOrigin')

    if isinstance(data, Image3D):
        data.origin += np.array(translationInMM)

    elif isinstance(data, Dynamic3DSequence):
        for image in data.dyn3DImageList:
            image.origin += np.array(translationInMM)

    elif isinstance(data, Dynamic3DModel):
        data.midp.origin += np.array(translationInMM)
        for df in data.deformationList:
            if df.velocity != None:
                df.origin += np.array(translationInMM)
            if df.displacement != None:
                df.origin += np.array(translationInMM)

    elif isinstance(data, ROIContour):
        print(NotImplementedError)

    else:
        print('translateDataByChangingOrigin not implemented on', type(data), 'yet. Abort')