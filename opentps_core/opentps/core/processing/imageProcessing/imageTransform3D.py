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
    """
    Extends all images to the same size and spacing, using the smallest spacing and the largest size.

    parameters
    ----------
    images: Sequence[Image3D]
        The images to extend.
    inPlace: bool
        Whether to modify the images in place. Default is False.
    fillValue: float
        The value to fill the new voxels with. Default is 0.

    returns
    -------
    Sequence[Image3D]
        The extended images if inPlace is False, otherwise the original images modified.
    """
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
    """
    Transforms an image from DICOM to IEC Gantry coordinates.

    parameters
    ----------
    image: Image3D
        The image to transform.
    beam: PlanIonBeam
        The beam to use for the transformation.
    fillValue: float
        The value to fill the new voxels with. Default is 0.
    cropROI: Optional[Union[ROIContour, ROIMask]]
        The ROI to crop the image to. Default is None.
    cropDim0: bool
        Whether to crop the image in the first dimension. Default is True.
    cropDim1: bool
        Whether to crop the image in the second dimension. Default is True.
    cropDim2: bool
        Whether to crop the image in the third dimension. Default is True.

    returns
    -------
    Image3D
        The transformed image.
    """
    logger.info("Resampling image DICOM -> IEC Gantry")

    tform = _forwardDicomToIECGantry(beam)

    tform = linalg.inv(tform)

    outImage = image.__class__.fromImage3D(image, patient=None)

    outputBox = _cropBoxAfterTransform(image, tform, cropROI, cropDim0, cropDim1, cropDim2)

    sitkImageProcessing.applyTransform3D(outImage, tform, fillValue=fillValue, outputBox=outputBox)

    return outImage

def _cropBox(image, tform, cropROI:Optional[Union[ROIContour, ROIMask]], cropDim0, cropDim1, cropDim2) -> Optional[Sequence[float]]:
    """
    Calculates the output box crop

    parameters
    ----------
    image: Image3D
        The image to transform.
    tform: np.ndarray
        The transformation matrix.
    cropROI: Optional[Union[ROIContour, ROIMask]]
        The ROI to crop the image to. Default is None.
    cropDim0: bool
        Whether to crop the image in the first dimension. Default is True.
    cropDim1: bool
        Whether to crop the image in the second dimension. Default is True.
    cropDim2: bool
        Whether to crop the image in the third dimension. Default is True.

    returns
    -------
    Optional[Sequence[float]]
        The output box coordinates with the format [x0, x1, y0, y1, z0, z1]
    """
    outputBox = "keepAll"

    if not (cropROI is None):
        outputBox = sitkImageProcessing.extremePointsAfterTransform(image, tform)
        outputBox = [elem for elem in outputBox]

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
    """
    Calculates the output box crop after a transformation.

    parameters
    ----------
    image: Image3D
        The image to transform.
    tform: np.ndarray
        The transformation matrix.
    cropROI: Optional[Union[ROIContour, ROIMask]]
        The ROI to crop the image to. Default is None.
    cropDim0: bool
        Whether to crop the image in the first dimension. Default is True.
    cropDim1: bool
        Whether to crop the image in the second dimension. Default is True.
    cropDim2: bool
        Whether to crop the image in the third dimension. Default is True.

    returns
    -------
    Optional[Sequence[float]]
        The output box coordinates with the format [x0, x1, y0, y1, z0, z1]
    """
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
    """
    Transforms a point from DICOM to IEC Gantry coordinates.

    parameters
    ----------
    beam: PlanIonBeam
        The beam to use for the transformation.
    point: Sequence[float]
        The point to transform coordinates [x, y, z].

    returns
    -------
    Sequence[float]
        The transformed point.
    """
    u = point[0]
    v = point[1]
    w = point[2]

    tform = _forwardDicomToIECGantry(beam)
    tform = linalg.inv(tform)

    return sitkImageProcessing.applyTransform3DToPoint(tform, np.array((u, v, w)))

def iecGantryToDicom(image:Image3D, beam:PlanIonBeam, fillValue:float=0, cropROI:Optional[Union[ROIContour, ROIMask]]=None,
                     cropDim0=True, cropDim1=True, cropDim2=True) -> Image3D:
    """
    Transforms an image from IEC Gantry to DICOM coordinates.

    parameters
    ----------
    image: Image3D
        The image to transform.
    beam: PlanIonBeam
        The beam to use for the transformation.
    fillValue: float
        The value to fill the image with outside the image. Default is 0.
    cropROI: Optional[Union[ROIContour, ROIMask]]
        The ROI to crop the image to. Default is None.
    cropDim0: bool
        Whether to crop the image in the first dimension. Default is True.
    cropDim1: bool
        Whether to crop the image in the second dimension. Default is True.
    cropDim2: bool
        Whether to crop the image in the third dimension. Default is True.

    returns
    -------
    Image3D
        The transformed image.
    """
    logger.info("Resampling image IEC Gantry -> DICOM")

    tform = _forwardDicomToIECGantry(beam)

    outputBox = _cropBox(image, tform, cropROI, cropDim0, cropDim1, cropDim2)

    outImage = image.__class__.fromImage3D(image, patient = None)
    sitkImageProcessing.applyTransform3D(outImage, tform, fillValue=fillValue, outputBox=outputBox)

    return outImage

def iecGantryCoordinatetoDicom(beam: PlanIonBeam, point: Sequence[float]) -> Sequence[float]:
    """
    Transforms a point from IEC Gantry to DICOM coordinates.

    parameters
    ----------
    beam: PlanIonBeam
        The beam to use for the transformation.
    point: Sequence[float]
        The point to transform coordinates [x, y, z].

    returns
    -------
    Sequence[float]
        The transformed point.
    """
    u = point[0]
    v = point[1]
    w = point[2]

    tform = _forwardDicomToIECGantry(beam)

    return sitkImageProcessing.applyTransform3DToPoint(tform, np.array((u, v, w)))

def _forwardDicomToIECGantry(beam:PlanIonBeam) -> np.ndarray:
    """
    Calculates the transformation matrix from DICOM to IEC Gantry coordinates.

    parameters
    ----------
    beam: PlanIonBeam
        The beam to use for the transformation.

    returns
    -------
    np.ndarray
        The transformation matrix.

    """
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
    """
    Calculates the rotation matrix for a roll.

    parameters
    ----------
    angle: float
        The angle of the roll in degrees.
    offset: Sequence[float]
        The offset of the rotation.

    returns
    -------
    np.ndarray
        The rotation matrix.
    """
    a = pi * angle / 180.
    ca = cos(a)
    sa = sin(a)

    R = [[ca, 0., sa, offset[0]],
         [0., 1., 0., offset[1]],
         [-sa, 0., ca, offset[2]],
         [0., 0., 0., 1.]]

    return np.array(R)

def _rot(angle:float, offset:Sequence[float]) -> np.ndarray:
    """
    Calculates the rotation matrix for a rotation around the z-axis.

    parameters
    ----------
    angle: float
        The angle of the rotation in degrees.
    offset: Sequence[float]
        The offset of the rotation.

    returns
    -------
    np.ndarray
        The rotation matrix.
    """
    a = pi * angle / 180.
    ca = cos(a)
    sa = sin(a)

    R = [[ca, -sa, 0., offset[0]],
         [sa, ca, 0., offset[1]],
         [0., 0., 1., offset[2]],
         [0., 0., 0., 1.]]

    return np.array(R)

def _pitch(angle:float, offset:Sequence[float]) -> np.ndarray:
    """
    Calculates the rotation matrix for a pitch.

    parameters
    ----------
    angle: float
        The angle of the pitch in degrees.
    offset: Sequence[float]

    returns
    -------
    np.ndarray
        The rotation matrix.
    """
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
    posInVoxels = np.round(np.divide(shiftedPosInMM, image3D.spacing)).astype(int)

    return posInVoxels

##---------------------------------------------------------------------------------------------------
def transform3DMatrixFromTranslationAndRotationsVectors(transVec=[0, 0, 0], rotVec=[0, 0, 0]):

    """
    Create a 4x4 affine transform matrix from a translation vector and a rotation vector.

    Parameters
    ----------
    transVec : list or tuple of 3 elements
        The translation vector in mm.
    rotVec : list or tuple of 3 elements
        The rotation vector in degrees.

    Returns
    -------
    np.ndarray
        The 4x4 affine transform matrix.
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

##---------------------------------------------------------------------------------------------------
def rotateVectorsInPlace(vectField, rotationArrayOrMatrix):
    """
    Rotate a vector field in place using a rotation matrix or a rotation vector.

    Parameters
    ----------
    vectField : VectorField3D
        The vector field to rotate.
    rotationArrayOrMatrix : np.ndarray
        The rotation matrix or rotation vector.
    """
    if rotationArrayOrMatrix.ndim == 1:
        r = R.from_rotvec(rotationArrayOrMatrix, degrees=True)
    elif rotationArrayOrMatrix.ndim == 2:
        if rotationArrayOrMatrix.shape[0] == 4:
            tformMatrix = rotationArrayOrMatrix[0:-1, 0:-1]
        r = R.from_matrix(tformMatrix)

    flattenedVectorField = vectField.imageArray.reshape((vectField.gridSize[0] * vectField.gridSize[1] * vectField.gridSize[2], 3))
    flattenedVectorField = r.apply(flattenedVectorField, inverse=True)

    vectField.imageArray = flattenedVectorField.reshape((vectField.gridSize[0], vectField.gridSize[1], vectField.gridSize[2], 3))

##---------------------------------------------------------------------------------------------------
def getTtransformMatrixInPixels(transformMatrixInMM, spacing):
    """
    Get the transform matrix in pixels from a transform matrix in mm.

    Parameters
    ----------
    transformMatrixInMM : np.ndarray
        The transform matrix in mm.
    spacing : list or tuple of 3 elements
        The spacing of the image.

    Returns
    -------
    np.ndarray
        The transform matrix in pixels.
    """

    transformMatrixInPixels = copy.copy(transformMatrixInMM)
    for i in range(3):
        transformMatrixInPixels[i, 3] = transformMatrixInPixels[i, 3] /spacing[i]

    return transformMatrixInPixels

##---------------------------------------------------------------------------------------------------
def translateData(data, translationInMM, outputBox='keepAll', fillValue=0, tryGPU=False, interpOrder=1, mode='constant'):
    """
    Translate the data by changing its origin.

    Parameters
    ----------
    data : Image3D or VectorField3D
        The data to translate.
    translationInMM : list or tuple of 3 elements
        The translation vector in mm.
    outputBox : str, optional
        The output box. The default is 'keepAll'.
    fillValue : int, optional
        The value to fill the empty voxels. The default is 0.
    tryGPU : bool, optional
        Try to use the GPU. The default is False.
    interpOrder : int, optional
        The interpolation order. The default is 1.
    mode : str, optional
        The mode for the interpolation. The default is 'constant'.
    """

    if not np.array(translationInMM == np.array([0, 0, 0])).all():
        if outputBox == 'keepAll':
            translateDataByChangingOrigin(data, translationInMM)
        else:
            if tryGPU:
                cupyImageProcessing.translateData(data, translationInMM=translationInMM, fillValue=fillValue, outputBox=outputBox, interpOrder=interpOrder, mode=mode)
            else:
                sitkImageProcessing.translateData(data, translationInMM=translationInMM, fillValue=fillValue, outputBox=outputBox)

##---------------------------------------------------------------------------------------------------
def rotateData(data, rotAnglesInDeg, outputBox='keepAll', fillValue=0, rotCenter='dicomOrigin', tryGPU=False, interpOrder=1, mode='constant'):
    """
    Rotate the data.

    Parameters
    ----------
    data : Image3D or VectorField3D
        The data to rotate.
    rotAnglesInDeg : list or tuple of 3 elements
        The rotation angles in degrees.
    outputBox : str, optional
        The output box. The default is 'keepAll'.
    fillValue : int, optional
        The value to fill the empty voxels. The default is 0.
    rotCenter : list or tuple of 3 elements, optional
        The rotation center. The default is 'dicomOrigin'.
    tryGPU : bool, optional
        Try to use the GPU. The default is False.
    interpOrder : int, optional
        The interpolation order. The default is 1.
    mode : str, optional
        The mode for the interpolation. The default is 'constant'.
    """
    if not np.array(rotAnglesInDeg == np.array([0, 0, 0])).all():
        if tryGPU:
            cupyImageProcessing.rotateData(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox, interpOrder=interpOrder, mode=mode)
        else:
            sitkImageProcessing.rotateData(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter)

##---------------------------------------------------------------------------------------------------
def applyTransform3D(data, tformMatrix:np.ndarray, fillValue:float=0, outputBox:Optional[Union[Sequence[float], str]]='keepAll',
    rotCenter: Optional[Union[Sequence[float], str]]='dicomOrigin', translation:Sequence[float]=[0, 0, 0], tryGPU=False, interpOrder=1, mode='constant'):
    """
    Apply a 3D transform to the data.

    Parameters
    ----------
    data : Image3D or VectorField3D
        The data to transform.
    tformMatrix : np.ndarray
        The transform matrix.
    fillValue : float, optional
        The value to fill the empty voxels. The default is 0.
    outputBox : str, optional
        The output box. The default is 'keepAll'.
    rotCenter : list or tuple of 3 elements, optional
        The rotation center. The default is 'dicomOrigin'.
    translation : list or tuple of 3 elements, optional
        The translation vector in mm. The default is [0, 0, 0].
    tryGPU : bool, optional
        Try to use the GPU. The default is False.
    interpOrder : int, optional
        The interpolation order. The default is 1.
    mode : str, optional
        The mode for the interpolation. The default is 'constant'.
    """
    if tryGPU:
        cupyImageProcessing.applyTransform3D(data, tformMatrix=tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter, translation=translation, interpOrder=interpOrder, mode=mode)
    else:
        sitkImageProcessing.applyTransform3D(data, tformMatrix=tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter, translation=translation)

##---------------------------------------------------------------------------------------------------
def parseRotCenter(rotCenterArg: Optional[Union[Sequence[float], str]], image: Image3D):
    """
    Parse the rotation center.

    Parameters
    ----------
    rotCenterArg : list or tuple of 3 elements, optional
        The rotation center. The default is 'dicomOrigin'.
    image : Image3D
        The image.

    Returns
    -------
    rotCenter : np.ndarray
        The rotation center.
    """
    rotCenter = np.array([0, 0, 0]).astype(float)

    if not (rotCenterArg is None):
        if len(rotCenterArg) == 3 and (isinstance(rotCenterArg[0], float) or isinstance(rotCenterArg[0], int)):
            rotCenter = rotCenterArg
        elif rotCenterArg == 'dicomOrigin':
            rotCenter = np.array([0, 0, 0]).astype(float)
        elif rotCenterArg == 'imgCorner':
            logger.warning("The imageCorner option for rotations uses the center of the pixel in the corner and not the corner of the pixel.")
            rotCenter = image.origin.astype(float)
        elif rotCenterArg == 'imgCenter':
            rotCenter = image.origin + (image.gridSizeInWorldUnit-1) / 2
        else:
            rotCenter = image.origin + (image.gridSizeInWorldUnit-1) / 2
            logger.warning("Rotation center not recognized, default value is used (image center).")

    return rotCenter

##---------------------------------------------------------------------------------------------------
def translateDataByChangingOrigin(data, translationInMM):
    """
    Translate the data by changing its origin.

    Parameters
    ----------
    data : Image3D or VectorField3D
        The data to translate.
    translationInMM : list or tuple of 3 elements
        The translation vector in mm.
    """

    if isinstance(data, Image3D):
        data.origin = data.origin.astype(float) + np.array(translationInMM)

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