import time
from typing import Optional, Sequence, Union
import numpy as np
from scipy.spatial.transform import Rotation as R

try:
    import SimpleITK as sitk
except:
    print('No module SimpleITK found')

from opentps.core.processing.imageProcessing import resampler3D
from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images._vectorField3D import VectorField3D

from opentps.core.data._roiContour import ROIContour
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.data._transform3D import Transform3D
from opentps.core.processing.imageProcessing.imageTransform3D import \
    transform3DMatrixFromTranslationAndRotationsVectors, parseRotCenter, rotateVectorsInPlace


def image3DToSITK(image: Image3D, type=np.float32):
    imageData = image.imageArray.astype(type)
    imageData = np.swapaxes(imageData, 0, 2)

    img = sitk.GetImageFromArray(imageData)
    img.SetOrigin(image.origin.tolist())
    img.SetSpacing(image.spacing.tolist())

    # TODO SetDirection from angles but it is not clear how angles is defined

    return img


def sitkImageToImage3D(sitkImage: sitk.Image, type=float):
    imageArray = np.array(sitk.GetArrayFromImage(sitkImage)).astype(type)
    imageArray = np.swapaxes(imageArray, 0, 2)
    image = Image3D(imageArray=imageArray, origin=sitkImage.GetOrigin(), spacing=sitkImage.GetSpacing())
    # TODO SetDirection from angles but it is not clear how angles is defined

    return image


def resize(image: Image3D, newSpacing: np.ndarray, newOrigin: Optional[np.ndarray] = None,
           newShape: Optional[np.ndarray] = None, fillValue: float = 0.):
    # print('in sitkImageProcessing resize', type(image))
    if newOrigin is None:
        newOrigin = image.origin
    newOrigin = np.array(newOrigin)

    newSpacing = np.array(newSpacing)

    if newShape is None:
        newShape = (image.origin - newOrigin + image.gridSize * image.spacing) / newSpacing
    newShape = np.array(newShape)
    newShape = np.ceil(newShape).astype(int)

    imgType = image.imageArray.dtype
    img = image3DToSITK(image)
    dimension = img.GetDimension()
    reference_image = sitk.Image(newShape.tolist(), img.GetPixelIDValue())
    reference_image.SetDirection(img.GetDirection())
    reference_image.SetOrigin(newOrigin.tolist())
    reference_image.SetSpacing(newSpacing.tolist())

    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(img.GetDirection())

    outImg = sitk.Resample(img, reference_image, transform, sitk.sitkLinear, fillValue)
    outData = np.array(sitk.GetArrayFromImage(outImg))

    if imgType == bool:
        outData[outData < 0.5] = 0
    outData = outData.astype(imgType)

    outData = np.swapaxes(outData, 0, 2)

    image.imageArray = outData
    image.origin = newOrigin
    image.spacing = newSpacing


def extremePoints(image: Image3D):
    img = image3DToSITK(image)

    extreme_points = [img.TransformIndexToPhysicalPoint(np.array([0, 0, 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([image.gridSize[0], 0, 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(
                          np.array([image.gridSize[0], image.gridSize[1], 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(
                          np.array([image.gridSize[0], image.gridSize[1], image.gridSize[2]]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(
                          np.array([image.gridSize[0], 0, image.gridSize[2]]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([0, image.gridSize[1], 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(
                          np.array([0, image.gridSize[1], image.gridSize[2]]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([0, 0, image.gridSize[2]]).astype(int).tolist())]

    return extreme_points


def extremePointsAfterTransform(image: Image3D, tformMatrix: np.ndarray,
                                rotCenter: Optional[Union[Sequence[float], str]] = 'dicomOrigin',
                                translation: Sequence[float] = [0, 0, 0]):
    img = image3DToSITK(image)

    if tformMatrix.shape[1] == 4:
        translation = tformMatrix[0:-1, -1]
        tformMatrix = tformMatrix[0:-1, 0:-1]

    dimension = img.GetDimension()

    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(tformMatrix.flatten())
    transform.Translate(translation)

    rotCenter = parseRotCenter(rotCenter, image)
    transform.SetCenter(rotCenter)

    extreme_points = extremePoints(image)

    inv_transform = transform.GetInverse()

    extreme_points_transformed = [inv_transform.TransformPoint(pnt) for pnt in extreme_points]
    min_x = min(extreme_points_transformed)[0]
    min_y = min(extreme_points_transformed, key=lambda p: p[1])[1]
    min_z = min(extreme_points_transformed, key=lambda p: p[2])[2]
    max_x = max(extreme_points_transformed)[0]
    max_y = max(extreme_points_transformed, key=lambda p: p[1])[1]
    max_z = max(extreme_points_transformed, key=lambda p: p[2])[2]

    return min_x, max_x, min_y, max_y, min_z, max_z


def applyTransform3D(data, tformMatrix: np.ndarray, fillValue: float = 0.,
                     outputBox: Optional[Union[Sequence[float], str]] = 'keepAll',
                     rotCenter: Optional[Union[Sequence[float], str]] = 'dicomOrigin',
                     translation: Sequence[float] = [0, 0, 0]):
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
        print('sitkImageProcessing.applyTransform3D not implemented on', type(data), 'yet. Abort')

    ## do we want a return here ?


def applyTransform3DToImage3D(image: Image3D, tformMatrix: np.ndarray, fillValue: float = 0.,
                              outputBox: Optional[Union[Sequence[float], str]] = 'keepAll',
                              rotCenter: Optional[Union[Sequence[float], str]] = 'dicomOrigin',
                              translation: Sequence[float] = [0, 0, 0]):
    imgType = image.imageArray.dtype

    img = image3DToSITK(image)

    if tformMatrix.shape[1] == 4:
        translation = tformMatrix[0:-1, -1]
        tformMatrix = tformMatrix[0:-1, 0:-1]

    dimension = img.GetDimension()

    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(tformMatrix.flatten())
    transform.Translate(translation)

    rotCenter = parseRotCenter(rotCenter, image)
    transform.SetCenter(rotCenter)

    if outputBox == 'keepAll':
        min_x, max_x, min_y, max_y, min_z, max_z = extremePointsAfterTransform(image, tformMatrix, rotCenter=rotCenter,
                                                                               translation=translation)

        output_origin = [min_x, min_y, min_z]
        output_size = [int((max_x - min_x) / image.spacing[0]) + 1, int((max_y - min_y) / image.spacing[1]) + 1,
                       int((max_z - min_z) / image.spacing[2]) + 1]
    elif outputBox == 'same':
        output_origin = image.origin.tolist()
        output_size = image.gridSize.astype(int).tolist()
    else:
        min_x = outputBox[0]
        max_x = outputBox[1]
        min_y = outputBox[2]
        max_y = outputBox[3]
        min_z = outputBox[4]
        max_z = outputBox[5]

        output_origin = [min_x, min_y, min_z]
        output_size = [int((max_x - min_x) / image.spacing[0]) + 1, int((max_y - min_y) / image.spacing[1]) + 1,
                       int((max_z - min_z) / image.spacing[2]) + 1]

    reference_image = sitk.Image(output_size, img.GetPixelIDValue())
    reference_image.SetOrigin(output_origin)
    reference_image.SetSpacing(image.spacing.tolist())
    reference_image.SetDirection(img.GetDirection())
    outImg = sitk.Resample(img, reference_image, transform, sitk.sitkLinear, fillValue)
    outData = np.array(sitk.GetArrayFromImage(outImg))

    if imgType == bool:
        outData[outData < 0.5] = 0
    outData = outData.astype(imgType)
    outData = np.swapaxes(outData, 0, 2)
    image.imageArray = outData
    image.origin = output_origin


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

    rotateVectorsInPlace(vectField, tformMatrix)
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


def applyTransform3DToPoint(tformMatrix: np.ndarray, pnt: np.ndarray, rotCenter: Optional[Sequence[float]] = [0, 0, 0],
                            translation: Sequence[float] = [0, 0, 0]):
    if tformMatrix.shape[1] == 4:
        translation = tformMatrix[0:-1, -1]
        tformMatrix = tformMatrix[0:-1, 0:-1]

    transform = sitk.AffineTransform(3)
    transform.SetMatrix(tformMatrix.flatten())
    transform.Translate(translation)

    transform.SetCenter(rotCenter)

    inv_transform = transform.GetInverse()

    return inv_transform.TransformPoint(pnt.tolist())


def connectComponents(image: Image3D):
    img = image3DToSITK(image, type='uint8')
    return sitkImageToImage3D(sitk.RelabelComponent(sitk.ConnectedComponent(img)))


def rotateData(data, rotAnglesInDeg, fillValue=-1000, rotCenter='imgCenter', outputBox='keepAll'):
    if not np.array(rotAnglesInDeg == np.array([0, 0, 0])).all():
        affTransformMatrix = transform3DMatrixFromTranslationAndRotationsVectors(rotVec=rotAnglesInDeg)
        applyTransform3D(data, affTransformMatrix, rotCenter=rotCenter, fillValue=fillValue, outputBox=outputBox)

    ## do we want a return here ?


def translateData(data, translationInMM, fillValue=-1000, outputBox='keepAll'):
    if not np.array(translationInMM == np.array([0, 0, 0])).all():
        affTransformMatrix = transform3DMatrixFromTranslationAndRotationsVectors(transVec=translationInMM)
        applyTransform3D(data, affTransformMatrix, fillValue=fillValue, outputBox=outputBox)

    ## do we want a return here ?


def register(fixed_image, moving_image, multimodal=True, fillValue: float = 0.):
    initial_transform = sitk.CenteredTransformInitializer(fixed_image, moving_image, sitk.Euler3DTransform(),
                                                          sitk.CenteredTransformInitializerFilter.GEOMETRY)

    registration_method = sitk.ImageRegistrationMethod()

    if multimodal:
        registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
        registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
        registration_method.SetMetricSamplingPercentage(0.05, seed=76926294)
    else:
        registration_method.SetMetricAsMeanSquares()
        registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
        registration_method.SetMetricSamplingPercentage(0.05, seed=76926294)

    registration_method.SetOptimizerAsRegularStepGradientDescent(learningRate=1.0, minStep=1e-6,
                                                                 numberOfIterations=1000)
    registration_method.SetOptimizerScalesFromPhysicalShift()

    registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    registration_method.SetInterpolator(sitk.sitkLinear)
    registration_method.SetInitialTransform(initial_transform, inPlace=False)

    composite_transform = registration_method.Execute(fixed_image, moving_image)
    moving_resampled = sitk.Resample(moving_image, fixed_image, composite_transform, sitk.sitkLinear, fillValue,
                                     moving_image.GetPixelID())

    print('Final metric value: {0}'.format(registration_method.GetMetricValue()))
    print('Optimizer\'s stopping condition, {0}'.format(registration_method.GetOptimizerStopConditionDescription()))
    print(composite_transform)
    final_transform = sitk.CompositeTransform(composite_transform).GetBackTransform()
    euler3d_transform = sitk.Euler3DTransform(final_transform)
    euler3d_transform.SetComputeZYX(True)
    tformMatrix = np.zeros((4, 4))
    tformMatrix[0:-1, -1] = euler3d_transform.GetTranslation()
    tformMatrix[0:-1, 0:-1] = np.array(euler3d_transform.GetMatrix()).reshape(3, 3)
    rotCenter = euler3d_transform.GetCenter()

    return tformMatrix, rotCenter, sitkImageToImage3D(moving_resampled)


def dilate(image: Image3D, radius: Union[float, Sequence[float]]):
    imgType = image.imageArray.dtype

    img = image3DToSITK(image, type=int)

    dilateFilter = sitk.BinaryDilateImageFilter()
    dilateFilter.SetKernelType(sitk.sitkBall)
    dilateFilter.SetKernelRadius(radius)
    outImg = dilateFilter.Execute(img)

    outData = np.array(sitk.GetArrayFromImage(outImg))
    if imgType == bool:
        outData[outData < 0.5] = 0
    outData = outData.astype(imgType)
    outData = np.swapaxes(outData, 0, 2)
    image.imageArray = outData


if __name__ == "__main__":
    data = np.random.randint(0, high=500, size=(216, 216, 216))
    data = data.astype('float32')

    image = Image3D(np.array(data), origin=(0, 0, 0), spacing=(1, 1, 1))
    imageITK = Image3D(np.array(data), origin=(0, 0, 0), spacing=(1, 1, 1))

    start = time.time()
    resize(imageITK, np.array([0.5, 0.5, 0.5]), newOrigin=imageITK.origin, newShape=imageITK.gridSize * 2, fillValue=0.)
    end = time.time()
    print('Simple ITK from shape ' + str(image.gridSize) + ' to shape ' + str(imageITK.gridSize) + ' in ' + str(
        end - start) + ' s')

    start = time.time()
    imageArrayCupy = resampler3D.resampleOpenMP(image.imageArray, image.origin, image.spacing, image.gridSize,
                                                imageITK.origin, imageITK.spacing, imageITK.gridSize,
                                                fillValue=0, outputType=None, tryGPU=True)
    end = time.time()
    print('Cupy from shape ' + str(image.gridSize) + ' to shape ' + str(imageArrayCupy.shape) + ' in ' + str(
        end - start) + ' s')

    start = time.time()
    imageArrayCupy = resampler3D.resampleOpenMP(image.imageArray, image.origin, image.spacing, image.gridSize,
                                                imageITK.origin, imageITK.spacing, imageITK.gridSize,
                                                fillValue=0, outputType=None, tryGPU=True)
    end = time.time()
    print('Cupy from shape ' + str(image.gridSize) + ' to shape ' + str(imageArrayCupy.shape) + ' in ' + str(
        end - start) + ' s')

    start = time.time()
    imageArrayCupy = resampler3D.resampleOpenMP(image.imageArray, image.origin, image.spacing, image.gridSize,
                                                imageITK.origin, imageITK.spacing, imageITK.gridSize,
                                                fillValue=0, outputType=None, tryGPU=True)
    end = time.time()
    print('Cupy from shape ' + str(image.gridSize) + ' to shape ' + str(imageArrayCupy.shape) + ' in ' + str(
        end - start) + ' s')

    start = time.time()
    imageArrayKevin = resampler3D.resampleOpenMP(image.imageArray, image.origin, image.spacing, image.gridSize,
                                                 imageITK.origin, imageITK.spacing, imageITK.gridSize,
                                                 fillValue=0, outputType=None, tryGPU=False)
    end = time.time()
    print('Kevin from shape ' + str(image.gridSize) + ' to shape ' + str(imageArrayCupy.shape) + ' in ' + str(
        end - start) + ' s')


