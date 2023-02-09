import numpy as np
import logging
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt
from typing import Optional, Sequence, Union
import copy

try:
    import cupy
    import cupyx
except:
    print('Warning: cupy not found.')
    
from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images._vectorField3D import VectorField3D
from opentps.core.data._roiContour import ROIContour
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.processing.imageProcessing.resampler3D import resample

logger = logging.getLogger(__name__)
## ------------------------------------------------------------------------------------------------
def translateData(data, translationInMM, fillValue=0, outputBox='keepAll'):
    """

    Parameters
    ----------
    data :
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
        applyTransform3D(data, affTransformMatrix, fillValue=fillValue, outputBox=outputBox)

## ------------------------------------------------------------------------------------------------
def rotateData(data, rotAnglesInDeg, fillValue=0, outputBox='keepAll'):
    """

    Parameters
    ----------
    data : ND numpy array, the data to rotate
    rotAnglesInDeg : the rotation in degrees around each axis, that will be applied successively in X,Y,Z order
    fillValue : the value to fill the data if points come, after rotation, from outside the image
    rotCenter :
    outputBox :
    Returns
    -------
    data, the rotated data

    """

    rotAnglesInDeg = np.array(rotAnglesInDeg)
    if not np.array(rotAnglesInDeg == np.array([0, 0, 0])).all():

        if isinstance(data, Dynamic3DModel):
            print('Rotate the Dynamic3DModel of', rotAnglesInDeg, 'degrees')
            print('Rotate dynamic 3D model - midp image')
            rotateData(data.midp, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox)

            for field in data.deformationList:
                if field.velocity != None:
                    print('Rotate dynamic 3D model - velocity field')
                    rotateData(field.velocity, rotAnglesInDeg=rotAnglesInDeg, fillValue=0, outputBox=outputBox)
                if field.displacement != None:
                    print('Rotate dynamic 3D model - displacement field')
                    rotateData(field.displacement, rotAnglesInDeg=rotAnglesInDeg, fillValue=0, outputBox=outputBox)

        elif isinstance(data, Dynamic3DSequence):
            print('Rotate Dynamic3DSequence of', rotAnglesInDeg, 'degrees')
            for image3D in data.dyn3DImageList:
                rotateData(image3D, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox)

        if isinstance(data, Image3D):

            from opentps.core.data.images._roiMask import ROIMask

            if isinstance(data, VectorField3D):
                print('Rotate VectorField3D of', rotAnglesInDeg, 'degrees')
                rotate3DVectorFields(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=0,  outputBox=outputBox)

            elif isinstance(data, ROIMask):
                print('Rotate ROIMask of', rotAnglesInDeg, 'degrees')
                rotateImage3D(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=0,  outputBox=outputBox)

            else:
                print('Rotate Image3D of', rotAnglesInDeg, 'degrees')
                rotateImage3D(data, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue,  outputBox=outputBox)
        # affTransformMatrix = transform3DMatrixFromTranslationAndRotationsVectors(rotVec=rotAnglesInDeg)
        # applyTransform3D(data, affTransformMatrix, rotCenter=rotCenter, fillValue=fillValue, outputBox=outputBox)

## ------------------------------------------------------------------------------------------------
def rotateImage3D(image, rotAnglesInDeg=[0, 0, 0], fillValue=0, outputBox='keepAll'):

    if image.spacing[0] != image.spacing[1] or image.spacing[1] != image.spacing[2] or image.spacing[2] != image.spacing[0]:
        initialSpacing = copy.copy(image.spacing)
        image = resample(image, spacing=[min(initialSpacing), min(initialSpacing), min(initialSpacing)])
        logger.info("The rotation of data using Cupy does not take into account heterogeneous spacing. Resampling in homogeneous spacing is done.")

    imgType = copy.copy(image.imageArray.dtype)

    if imgType == bool:
        image.imageArray = image.imageArray.astype(np.float)

    cupyArray = cupy.asarray(image.imageArray)

    if outputBox == 'same':
        reshape = False
    elif outputBox == 'keepAll':
        print('cupyImageProcessing.rotateImage3D does not work with outputBox="keepAll" for now, "same" is used instead.')
        ## the origin of the image must be adapted in this case
        reshape = False

    if rotAnglesInDeg[0] != 0:
        # print('Apply rotation around X', rotAnglesInDeg[0])
        cupyArray = cupyx.scipy.ndimage.rotate(cupyArray, -rotAnglesInDeg[0], axes=[1, 2], reshape=reshape, mode='constant', cval=fillValue)
    if rotAnglesInDeg[1] != 0:
        # print('Apply rotation around Y', rotAnglesInDeg[1])
        cupyArray = cupyx.scipy.ndimage.rotate(cupyArray, -rotAnglesInDeg[1], axes=[0, 2], reshape=reshape, mode='constant', cval=fillValue)
    if rotAnglesInDeg[2] != 0:
        # print('Apply rotation around Z', rotAnglesInDeg[2])
        cupyArray = cupyx.scipy.ndimage.rotate(cupyArray, -rotAnglesInDeg[2], axes=[0, 1], reshape=reshape, mode='constant', cval=fillValue)

    outData = cupy.asnumpy(cupyArray)

    if imgType == bool:
        outData[outData < 0.5] = 0
    outData = outData.astype(imgType)
    image.imageArray = outData

    if initialSpacing[0] != initialSpacing[1] or initialSpacing[1] != initialSpacing[2] or initialSpacing[2] != initialSpacing[0]:
        image = resample(image, spacing=initialSpacing)
        logger.info("Resampling in the initial spacing is done.")
    return image

## ------------------------------------------------------------------------------------------------
def rotate3DVectorFields(vectorField, rotAnglesInDeg=[0, 0, 0], fillValue=0, outputBox='keepAll'):

    """

    Parameters
    ----------
    vectorField
    rotationInDeg

    Returns
    -------

    """

    print('Apply rotation to field imageArray', rotAnglesInDeg)
    rotateImage3D(vectorField, rotAnglesInDeg=rotAnglesInDeg, fillValue=fillValue, outputBox=outputBox)

    print('Apply rotation to field vectors', rotAnglesInDeg)
    from opentps.core.processing.imageProcessing.imageTransform3D import rotateVectorsInPlace
    rotateVectorsInPlace(vectorField, -rotAnglesInDeg)

## ------------------------------------------------------------------------------------------------
def applyTransform3D(data, tformMatrix: np.ndarray, fillValue: float = 0.,
                     outputBox: Optional[Union[Sequence[float], str]] = 'keepAll',
                     rotCenter: Optional[Union[Sequence[float], str]] = 'dicomOrigin',
                     translation: Sequence[float] = [0, 0, 0]):

    from opentps.core.data._transform3D import Transform3D

    if isinstance(tformMatrix, Transform3D):
        tformMatrix = tformMatrix.tformMatrix

    if isinstance(data, Image3D):

        from opentps.core.data.images._roiMask import ROIMask

        if isinstance(data, VectorField3D):
            applyTransform3DToVectorField3D(data, tformMatrix, fillValue=0, outputBox=outputBox, rotCenter=rotCenter,
                                            translation=translation)
        elif isinstance(data, ROIMask):
            applyTransform3DToImage3D(data, tformMatrix, fillValue=0, outputBox=outputBox, rotCenter=rotCenter,
                                      translation=translation)
        else:
            applyTransform3DToImage3D(data, tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter,
                                      translation=translation)

    elif isinstance(data, Dynamic3DSequence):
        for image in data.dyn3DImageList:
            applyTransform3DToImage3D(image, tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter,
                                      translation=translation)

    elif isinstance(data, Dynamic3DModel):
        applyTransform3DToImage3D(data.midp, tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter,
                                  translation=translation)
        for df in data.deformationList:
            if df.velocity != None:
                applyTransform3DToVectorField3D(df.velocity, tformMatrix, fillValue=0, outputBox=outputBox,
                                                rotCenter=rotCenter, translation=translation)
            if df.displacement != None:
                applyTransform3DToVectorField3D(df.displacement, tformMatrix, fillValue=0, outputBox=outputBox,
                                                rotCenter=rotCenter, translation=translation)

    elif isinstance(data, ROIContour):
        print(NotImplementedError)

    else:
        print('cupyImageProcessing.applyTransform3D not implemented on', type(data), 'yet. Abort')

    ## do we want a return here ?

## ------------------------------------------------------------------------------------------------
def applyTransform3DToImage3D(image: Image3D, tformMatrix: np.ndarray, fillValue: float = 0.,
                              outputBox: Optional[Union[Sequence[float], str]] = 'keepAll',
                              rotCenter: Optional[Union[Sequence[float], str]] = 'dicomOrigin',
                              translation: Sequence[float] = [0, 0, 0]):

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

    cupyImg = cupyx.scipy.ndimage.affine_transform(cupyImg, cupyTformMatrix, order=3, mode='constant', cval=fillValue)

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
                                    translation: Sequence[float] = [0, 0, 0]):
    vectorFieldCompList = []
    for i in range(3):
        compImg = Image3D.fromImage3D(vectField)
        compImg.imageArray = vectField.imageArray[:, :, :, i]

        applyTransform3DToImage3D(compImg, tformMatrix, fillValue=fillValue, outputBox=outputBox, rotCenter=rotCenter,
                                  translation=translation)

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

    print('ici')
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