import numpy as np
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt
from typing import Optional, Sequence, Union
import copy
import logging
logger = logging.getLogger(__name__)

try:
    import cupy
    import cupyx
except:
    logger.warning("Cannot import Cupy module")
    pass
    
from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images._vectorField3D import VectorField3D
from opentps.core.data._roiContour import ROIContour
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.processing.imageProcessing.roiMasksProcessing import buildStructElem

## ------------------------------------------------------------------------------------------------
def translateData(data, translationInMM, fillValue=0, outputBox='keepAll', interpOrder=1, mode='constant'):
    """
    Parameters
    ----------
    data : Image3D or Dynamic3DSequence or Dynamic3DModel
    translationInMM : sequence of the translation in millimeters in the 3 direction [X, Y, Z]
    fillValue : the value to fill the data for points coming, after translation, from outside the image
    outputBox : the cube in space represented by the result after translation
    Returns
    -------
    the translated data
    """

    if not np.array(translationInMM == np.array([0, 0, 0])).all():
        from opentps.core.processing.imageProcessing.imageTransform3D import \
            transform3DMatrixFromTranslationAndRotationsVectors
        affTransformMatrix = transform3DMatrixFromTranslationAndRotationsVectors(transVec=translationInMM)
        applyTransform3D(data, affTransformMatrix, fillValue=fillValue, outputBox=outputBox, interpOrder=interpOrder, mode=mode)

## ------------------------------------------------------------------------------------------------
def rotateData(data, rotAnglesInDeg, fillValue=0, outputBox='keepAll', interpOrder=1, mode='constant'):
    """
    Parameters
    ----------
    data : Image3D or Dynamic3DSequence or Dynamic3DModel
        data to be rotated.
    rotAnglesInDeg : sequence[float]
        rotation angles in degrees in the 3 directions [X, Y, Z]
    fillValue : float
        the value to fill the data for points coming, after rotation, from outside the image
    outputBox : str
        the cube in space represented by the result after rotation
    interpOrder : int
        the order of the interpolation
    mode : str
        the mode of the interpolation

    Returns
    -------
    data, the rotated data
    """

    rotAnglesInDeg = np.array(rotAnglesInDeg)
    if not np.array(rotAnglesInDeg == np.array([0, 0, 0])).all():

        if isinstance(data, Dynamic3DModel):
            logger.info(f'Rotate the Dynamic3DModel of {rotAnglesInDeg} degrees')
            logger.info('Rotate dynamic 3D model - midp image')
            rotateData(data.midp, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox, interpOrder=interpOrder, mode=mode)

            for field in data.deformationList:
                if field.velocity != None:
                    logger.info('Rotate dynamic 3D model - velocity field')
                    rotateData(field.velocity, rotAnglesInDeg=rotAnglesInDeg, fillValue=0, outputBox=outputBox, interpOrder=interpOrder, mode=mode)
                if field.displacement != None:
                    logger.info('Rotate dynamic 3D model - displacement field')
                    rotateData(field.displacement, rotAnglesInDeg=rotAnglesInDeg, fillValue=0, outputBox=outputBox, interpOrder=interpOrder, mode=mode)

        elif isinstance(data, Dynamic3DSequence):
            logger.info(f'Rotate Dynamic3DSequence of {rotAnglesInDeg} degrees')
            for image3D in data.dyn3DImageList:
                rotateData(image3D, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox, interpOrder=interpOrder, mode=mode)

        if isinstance(data, Image3D):

            from opentps.core.data.images._roiMask import ROIMask

            if isinstance(data, VectorField3D):
                logger.info(f'Rotate VectorField3D of {rotAnglesInDeg} degrees')
                rotate3DVectorFields(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=0,  outputBox=outputBox, interpOrder=interpOrder, mode=mode)

            elif isinstance(data, ROIMask):
                logger.info(f'Rotate ROIMask of {rotAnglesInDeg} degrees')
                rotateImage3D(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=0,  outputBox=outputBox, interpOrder=interpOrder, mode=mode)

            else:
                logger.info(f'Rotate Image3D of {rotAnglesInDeg} degrees')
                rotateImage3D(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue,  outputBox=outputBox, interpOrder=interpOrder, mode=mode)

        # affTransformMatrix = transform3DMatrixFromTranslationAndRotationsVectors(rotVec=rotAnglesInDeg)
        # applyTransform3D(data, affTransformMatrix, rotCenter=rotCenter, fillValue=fillValue, outputBox=outputBox)

## ------------------------------------------------------------------------------------------------
def rotateImage3D(image, rotAnglesInDeg=[0, 0, 0], fillValue=0, outputBox='keepAll', interpOrder=1, mode='constant'):
    """
    rotate image3D around its center

    Parameters
    ----------
    image : Image3D
        the image to be rotated
    rotAnglesInDeg : sequence[float]
        rotation angles in degrees in the 3 directions [X, Y, Z]
    fillValue : float
        the value to fill the data for points coming, after rotation, from outside the image
    outputBox : str
        the cube in space represented by the result after rotation
    interpOrder : int
        the order of the interpolation
    mode : str
        the mode of the interpolation
    """
    resampled = False
    if image.spacing[0] != image.spacing[1] or image.spacing[1] != image.spacing[2] or image.spacing[2] != image.spacing[0]:
        initialSpacing = copy.copy(image.spacing)
        initialGridSize = copy.copy(image.gridSize)
        initialOrigin = copy.copy(image.origin)
        resampled = True
        from opentps.core.processing.imageProcessing.resampler3D import resample
        resample(image, spacing=[min(initialSpacing), min(initialSpacing), min(initialSpacing)], inPlace=True)
        logger.info("The rotation of data using Cupy does not take into account heterogeneous spacing. Resampling in homogeneous spacing is done.")

    imgType = copy.copy(image.imageArray.dtype)

    if imgType == bool:
        image.imageArray = image.imageArray.astype(np.float)

    cupyArray = cupy.asarray(image.imageArray)

    if outputBox == 'same':
        reshape = False
    elif outputBox == 'keepAll':
        logger.error("cupyImageProcessing.rotateImage3D does not work with outputBox=keepAll for now. Abort.")
        raise NotImplementedError

    if rotAnglesInDeg[0] != 0:
        # print('Apply rotation around X', rotAnglesInDeg[0])
        cupyArray = cupyx.scipy.ndimage.rotate(cupyArray, -rotAnglesInDeg[0], axes=[1, 2], order=interpOrder, reshape=reshape, mode=mode, cval=fillValue)
    if rotAnglesInDeg[1] != 0:
        #print('Apply rotation around Y', rotAnglesInDeg[1])
        cupyArray = cupyx.scipy.ndimage.rotate(cupyArray, -rotAnglesInDeg[1], axes=[0, 2], order=interpOrder, reshape=reshape, mode=mode, cval=fillValue)
    if rotAnglesInDeg[2] != 0:
        # print('Apply rotation around Z', rotAnglesInDeg[2])
        cupyArray = cupyx.scipy.ndimage.rotate(cupyArray, -rotAnglesInDeg[2], axes=[0, 1], order=interpOrder, reshape=reshape, mode=mode, cval=fillValue)

    outData = cupy.asnumpy(cupyArray)

    if imgType == bool:
        outData[outData < 0.5] = 0
    outData = outData.astype(imgType)
    image.imageArray = outData

    if resampled:
        resample(image, origin=initialOrigin, gridSize=initialGridSize, spacing=initialSpacing, inPlace=True)
        logger.info("Resampling in the initial spacing is applied after rotation")

## ------------------------------------------------------------------------------------------------
def rotate3DVectorFields(vectorField, rotAnglesInDeg=[0, 0, 0], fillValue=0, outputBox='keepAll', interpOrder=1, mode='constant'):

    """
    Rotate a vector field around its center

    Parameters
    ----------
    vectorField : VectorField3D
        the vector field to be rotated
    rotationInDeg : sequence[float]
        rotation angles in degrees in the 3 directions [X, Y, Z]
    fillValue : float
        the value to fill the data for points coming, after rotation, from outside the image. Default is 0
    outputBox : str
        the cube in space represented by the result after rotation (same, keepAll). Default is keepAll

    interpOrder : int
        the order of the interpolation (0, 1, 2, 3, 4) default is 1
    mode : str
        the mode of the interpolation (constant, nearest, reflect, wrap). Default is constant
    """

    logger.info(f'Apply rotation of {rotAnglesInDeg} degrees to field imageArray')
    rotateImage3D(vectorField, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox, interpOrder=interpOrder, mode=mode)

    logger.info(f'Apply rotation of {rotAnglesInDeg} degrees to field vectors')
    from opentps.core.processing.imageProcessing.imageTransform3D import rotateVectorsInPlace
    rotateVectorsInPlace(vectorField, -rotAnglesInDeg)

## ------------------------------------------------------------------------------------------------
def applyTransform3D(data, tformMatrix: np.ndarray, fillValue: float = 0.,
                     outputBox: Optional[Union[Sequence[float], str]] = 'keepAll',
                     rotCenter: Optional[Union[Sequence[float], str]] = 'dicomOrigin',
                     translation: Sequence[float] = [0, 0, 0],
                     interpOrder=1, mode='constant'):
    """
    Apply a 3D transformation to an image or a vector field

    Parameters
    ----------
    data : Image3D or VectorField3D
        the data to be transformed
    tformMatrix : np.ndarray
        the transformation matrix
    fillValue : float
        the value to fill the data for points coming, after rotation, from outside the image. Default is 0
    outputBox : str
        the cube in space represented by the result after rotation ('same', 'keepAll'). Default is 'keepAll'
    rotCenter : str or sequence[float]
        the center of rotation. Default is dicomOrigin
    translation : sequence[float]
        the translation to apply to the data after rotation. Default is [0, 0, 0]
    interpOrder : int
        the order of the interpolation (0, 1, 2, 3, 4) default is 1
    mode : str
        the mode of the interpolation ('constant', 'nearest', 'reflect', 'wrap'). Default is 'constant'
    """

    from opentps.core.data._transform3D import Transform3D

    if isinstance(tformMatrix, Transform3D):
        tformMatrix = tformMatrix.tformMatrix

    if isinstance(data, Image3D):

        from opentps.core.data.images._roiMask import ROIMask

        if isinstance(data, VectorField3D):
            applyTransform3DToVectorField3D(data, tformMatrix, fillValue=0, outputBox=outputBox, rotCenter=rotCenter,
                                            translation=translation, interpOrder=interpOrder, mode=mode)
        elif isinstance(data, ROIMask):
            applyTransform3DToImage3D(data, tformMatrix, fillValue=0, outputBox=outputBox, rotCenter=rotCenter,
                                      translation=translation, interpOrder=interpOrder, mode=mode)
        else:
            applyTransform3DToImage3D(data, tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter,
                                      translation=translation, interpOrder=interpOrder, mode=mode)

    elif isinstance(data, Dynamic3DSequence):
        for image in data.dyn3DImageList:
            applyTransform3DToImage3D(image, tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter,
                                      translation=translation, interpOrder=interpOrder, mode=mode)

    elif isinstance(data, Dynamic3DModel):
        applyTransform3DToImage3D(data.midp, tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter,
                                  translation=translation, interpOrder=interpOrder, mode=mode)
        for df in data.deformationList:
            if df.velocity != None:
                applyTransform3DToVectorField3D(df.velocity, tformMatrix, fillValue=0, outputBox=outputBox,
                                                rotCenter=rotCenter, translation=translation, interpOrder=interpOrder, mode=mode)
            if df.displacement != None:
                applyTransform3DToVectorField3D(df.displacement, tformMatrix, fillValue=0, outputBox=outputBox,
                                                rotCenter=rotCenter, translation=translation, interpOrder=interpOrder, mode=mode)

    elif isinstance(data, ROIContour):
        raise NotImplementedError

    else:
        logger.error(f'cupyImageProcessing.applyTransform3D not implemented on {type(data)} yet. Abort')
        raise NotImplementedError

    ## do we want a return here ?

## ------------------------------------------------------------------------------------------------
def applyTransform3DToImage3D(image: Image3D, tformMatrix: np.ndarray, fillValue: float = 0.,
                              outputBox: Optional[Union[Sequence[float], str]] = 'keepAll',
                              rotCenter: Optional[Union[Sequence[float], str]] = 'dicomOrigin',
                              translation: Sequence[float] = [0, 0, 0], interpOrder=1, mode='constant'):
    """
    Apply a 3D transformation to an image

    Parameters
    ----------
    image : Image3D
        the image to be transformed
    tformMatrix : np.ndarray
        the transformation matrix
    fillValue : float
        the value to fill the data for points coming, after rotation, from outside the image. Default is 0
    outputBox : str
        the cube in space represented by the result after rotation ('same', 'keepAll'). Default is 'keepAll'
    rotCenter : str or sequence[float]
        the center of rotation. Default is 'dicomOrigin'
    translation : sequence[float]
        the translation to apply to the data after rotation. Default is [0, 0, 0]
    interpOrder : int
        the order of the interpolation (0, 1, 2, 3, 4) default is 1
    mode : str
        the mode of the interpolation ('constant', 'nearest', 'reflect', 'wrap'). Default is 'constant'
    """
    imgType = copy.copy(image.imageArray.dtype)

    if imgType == bool:
        image.imageArray = image.imageArray.astype(np.float)

    if tformMatrix.shape[1] == 3:
        completeMatrix = np.zeros((4, 4))
        completeMatrix[0:3, 0:3] = tformMatrix
        completeMatrix[3, 3] = 1
        tformMatrix = completeMatrix

    from opentps.core.processing.imageProcessing.imageTransform3D import getTtransformMatrixInPixels
    tformMatrix = getTtransformMatrixInPixels(tformMatrix, image.spacing)

    cupyTformMatrix = cupy.asarray(tformMatrix)

    cupyImg = cupy.asarray(image.imageArray)

    from opentps.core.processing.imageProcessing.imageTransform3D import parseRotCenter
    rotCenter = parseRotCenter(rotCenter, image)

    cupyImg = cupyx.scipy.ndimage.affine_transform(cupyImg, cupyTformMatrix, order=interpOrder, mode=mode, cval=fillValue)

    outData = cupy.asnumpy(cupyImg)

    if imgType == bool:
        outData[outData < 0.5] = 0
    outData = outData.astype(imgType)
    image.imageArray = outData
    # image.origin = output_origin

## ------------------------------------------------------------------------------------------------
def applyTransform3DToVectorField3D(vectField: VectorField3D, tformMatrix: np.ndarray, fillValue: float = 0.,
                                    outputBox: Optional[Union[Sequence[float], str]] = 'keepAll',
                                    rotCenter: Optional[Union[Sequence[float], str]] = 'dicomOrigin',
                                    translation: Sequence[float] = [0, 0, 0], interpOrder=1, mode='constant'):
    """
    Apply a 3D transformation to a vector field

    Parameters
    ----------
    vectField : VectorField3D
        the vector field to be transformed
    tformMatrix : np.ndarray
        the transformation matrix
    fillValue : float
        the value to fill the data for points coming, after rotation, from outside the image. Default is 0
    outputBox : str
        the cube in space represented by the result after rotation ('same', 'keepAll'). Default is 'keepAll'
    rotCenter : str or sequence[float]
        the center of rotation. Default is 'dicomOrigin'
    translation : sequence[float]
        the translation to apply to the data after rotation. Default is [0, 0, 0]
    interpOrder : int
        the order of the interpolation (0, 1, 2, 3, 4) default is 1
    mode : str
        the mode of the interpolation ('constant', 'nearest', 'reflect', 'wrap'). Default is 'constant'
    """
    vectorFieldCompList = []
    for i in range(3):
        compImg = Image3D.fromImage3D(vectField)
        compImg.imageArray = vectField.imageArray[:, :, :, i]

        applyTransform3DToImage3D(compImg, tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter,
                                  translation=translation, interpOrder=interpOrder, mode=mode)

        vectorFieldCompList.append(compImg.imageArray)

    vectField.imageArray = np.stack(vectorFieldCompList, axis=3)
    vectField.origin = compImg.origin

    # if tformMatrix.shape[1] == 4:
    #     tformMatrix = tformMatrix[0:-1, 0:-1]
    #
    # r = R.from_matrix(tformMatrix)
    #
    # flattenedVectorField = vectField.imageArray.reshape(
    #     (vectField.gridSize[0] * vectField.gridSize[1] * vectField.gridSize[2], 3))
    # flattenedVectorField = r.apply(flattenedVectorField, inverse=True)
    #
    # vectField.imageArray = flattenedVectorField.reshape(
    #     (vectField.gridSize[0], vectField.gridSize[1], vectField.gridSize[2], 3))


## ------------------------------------------------------------------------------------------------
def rotateUsingMapCoordinatesCupy(img, rotAngleInDeg, rotAxis=1):
    """

    DOES NOT WORK FOR NOW
    WIP
    Parameters
    ----------
    img
    rotAngleInDeg
    rotAxis

    Returns
    -------

    """
    voxelCoordsAroundCenterOfImageX = np.linspace((-img.gridSize[0] / 2) + 0.5, (img.gridSize[0] / 2) + 0.5, num=img.gridSize[0]) * img.spacing[0]
    voxelCoordsAroundCenterOfImageY = np.linspace((-img.gridSize[1] / 2) + 0.5, (img.gridSize[1] / 2) + 0.5, num=img.gridSize[1]) * img.spacing[1]
    voxelCoordsAroundCenterOfImageZ = np.linspace((-img.gridSize[2] / 2) + 0.5, (img.gridSize[2] / 2) + 0.5, num=img.gridSize[2]) * img.spacing[2]

    x, y, z = np.meshgrid(voxelCoordsAroundCenterOfImageX, voxelCoordsAroundCenterOfImageY, voxelCoordsAroundCenterOfImageZ, indexing='ij')
    print(img.spacing)
    print(voxelCoordsAroundCenterOfImageX[:10])
    print(voxelCoordsAroundCenterOfImageY[:10])

    coordsMatrix = np.stack((x, y, z), axis=-1)

    print(coordsMatrix.shape)

    # test = np.roll(np.array([1, 0, 0]), rotAxis)
    r = R.from_rotvec(rotAngleInDeg * np.roll(np.array([1, 0, 0]), rotAxis), degrees=True)
    print(r.as_matrix())

    coordsVector = coordsMatrix.reshape((coordsMatrix.shape[0] * coordsMatrix.shape[1] * coordsMatrix.shape[2], 3))
    # voxel = 4000
    # print(flattenedVectorField.shape)
    # print(flattenedVectorField[voxel])

    rotatedCoordsVector = r.apply(coordsVector, inverse=True)

    # print(flattenedVectorField.shape)
    # print(flattenedVectorField[voxel])

    rotatedCoordsMatrix = rotatedCoordsVector.reshape((coordsMatrix.shape[0], coordsMatrix.shape[1], coordsMatrix.shape[2], 3))
    # print(coordsVector[:10])
    # np.stack((a, b), axis=-1)

    print(rotatedCoordsMatrix.shape)
    print(img.imageArray.shape)
    # rotatedCoordsAndValue = np.concatenate((rotatedCoordsMatrix, img.imageArray))
    rotatedCoordsAndValue = np.stack((rotatedCoordsMatrix, img.imageArray), axis=1)
    print(rotatedCoordsAndValue.shape)

    interpolatedImage = cupy.asnumpy(cupyx.scipy.ndimage.map_coordinates(cupy.asarray(image), cupy.asarray(coordsMatrix), order=1, mode='constant', cval=-1000))

    # print(voxelCoordsAroundCenterOfImageX)

    cupyArray = cupy.asarray(img.imageArray)

## ------------------------------------------------------------------------------------------------
def resampleCupy():
    """
    TODO
    Returns
    -------

    """

    return NotImplementedError

def dilateMask(mask, radius=1.0, struct=None, inPlace=True):
    """
    dilate a mask by a given radius

    Parameters
    ----------
    mask : Image3D
        the mask to dilate
    radius : float
        the radius of the dilation in mm. Default is 1.0
    struct : ndarray
        the structuring element to use for the dilation. Default is None
    inPlace : bool
        if True, the mask is dilated in place, if False, a copy of the mask is returned. Default is True

    Returns
    -------
    Image3D
        the dilated mask if inPlace is False, None otherwise
    """
    if struct is None:
        radius = radius / np.array(mask.spacing)
        struct = buildStructElem(radius)
    if inPlace:
        mask.imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_dilation(cupy.asarray(mask.imageArray), structure=cupy.asarray(struct)))
    else:
        maskCopy = mask.copy()
        maskCopy.imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_dilation(cupy.asarray(maskCopy.imageArray), structure=cupy.asarray(struct)))
        return maskCopy

def erodeMask(mask, radius=1.0, struct=None, inPlace=True):
    """
    erode a mask by a given radius

    Parameters
    ----------
    mask : Image3D
        the mask to erode
    radius : float
        the radius of the erosion in mm. Default is 1.0
    struct : ndarray
        the structuring element to use for the erosion. Default is None
    inPlace : bool
        if True, the mask is eroded in place, if False, a copy of the mask is returned. Default is True

    Returns
    -------
    Image3D
        the eroded mask if inPlace is False, None otherwise
    """

    if struct is None:
        radius = radius / np.array(mask.spacing)
        struct = buildStructElem(radius)
    if inPlace:
        mask.imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_erosion(cupy.asarray(mask.imageArray), structure=cupy.asarray(struct)))
    else:
        maskCopy = mask.copy()
        maskCopy.imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_erosion(cupy.asarray(maskCopy.imageArray), structure=cupy.asarray(struct)))
        return maskCopy

def openMask(mask, radius=1.0, struct=None, inPlace=True):
    """
    open a mask by a given radius

    Parameters
    ----------
    mask : Image3D
        the mask to open
    radius : float
        the radius of the opening in mm. Default is 1.0
    struct : ndarray
        the structuring element to use for the opening. Default is None
    inPlace : bool
        if True, the mask is opened in place, if False, a copy of the mask is returned. Default is True

    Returns
    -------
    Image3D
        the opened mask if inPlace is False, None otherwise
    """
    if struct is None:
        radius = radius / np.array(mask.spacing)
        struct = buildStructElem(radius)
    if inPlace:
        mask.imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_opening(cupy.asarray(mask.imageArray), structure=cupy.asarray(struct)))
    else:
        maskCopy = mask.copy()
        maskCopy.imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_opening(cupy.asarray(maskCopy.imageArray), structure=cupy.asarray(struct)))
        return maskCopy

def closeMask(mask, radius=1.0, struct=None, inPlace=True):
    """
    close a mask by a given radius

    Parameters
    ----------
    mask : Image3D
        the mask to close
    radius : float
        the radius of the closing in mm. Default is 1.0
    struct : ndarray
        the structuring element to use for the closing. Default is None
    inPlace : bool
        if True, the mask is closed in place, if False, a copy of the mask is returned. Default is True

    Returns
    -------
    Image3D
        the closed mask if inPlace is False, None otherwise
    """
    if struct is None:
        radius = radius / np.array(mask.spacing)
        struct = buildStructElem(radius)
    if inPlace:
        mask.imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_closing(cupy.asarray(mask.imageArray), structure=cupy.asarray(struct)))
    else:
        maskCopy = mask.copy()
        maskCopy.imageArray = cupy.asnumpy(cupyx.scipy.ndimage.binary_closing(cupy.asarray(maskCopy.imageArray), structure=cupy.asarray(struct)))
        return maskCopy

def gaussianSmoothing(imgArray, sigma=1, truncate=2.5, mode="reflect"):
    """
    smooth an image with a gaussian filter

    Parameters
    ----------
    imgArray : ndarray
        the image to smooth
    sigma : float
        the sigma of the gaussian filter. Default is 1
    truncate : float
        the truncation of the gaussian filter. Default is 2.5
    mode : str
        the mode of the gaussian filter. Default is "reflect"

    Returns
    -------
    ndarray
        the smoothed image
    """
    cupyNewImg = cupy.asarray(imgArray)
    smoothedImg = cupy.asnumpy(cupyx.scipy.ndimage.gaussian_filter(cupyNewImg, sigma=sigma, truncate=truncate, mode=mode))
    return smoothedImg