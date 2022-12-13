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
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.data._transform3D import Transform3D
from opentps.core.processing.imageProcessing.imageTransform3D import transform3DMatrixFromTranslationAndRotationsVectors


def image3DToSITK(image:Image3D, type=np.float32):

    imageData = image.imageArray.astype(type)
    imageData = np.swapaxes(imageData, 0, 2)
    
    img = sitk.GetImageFromArray(imageData)
    img.SetOrigin(image.origin.tolist())
    img.SetSpacing(image.spacing.tolist())

    # TODO SetDirection from angles but it is not clear how angles is defined

    return img

def sitkImageToImage3D(sitkImage:sitk.Image, type=float):
    imageArray = np.array(sitk.GetArrayFromImage(sitkImage)).astype(type)
    imageArray = np.swapaxes(imageArray, 0, 2)
    image = Image3D(imageArray=imageArray,origin=sitkImage.GetOrigin(), spacing=sitkImage.GetSpacing())
    # TODO SetDirection from angles but it is not clear how angles is defined

    return image

def resize(image:Image3D, newSpacing:np.ndarray, newOrigin:Optional[np.ndarray]=None, newShape:Optional[np.ndarray]=None, fillValue:float=0.):
    # print('in sitkImageProcessing resize', type(image))
    if newOrigin is None:
        newOrigin = image.origin
    newOrigin = np.array(newOrigin)

    newSpacing = np.array(newSpacing)

    if newShape is None:
        newShape = (image.origin - newOrigin + image.gridSize*image.spacing)/newSpacing
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

    if imgType==bool:
        outData[outData<0.5] = 0
    outData = outData.astype(imgType)

    outData = np.swapaxes(outData, 0, 2)

    image.imageArray = outData
    image.origin = newOrigin
    image.spacing = newSpacing


def extremePoints(image:Image3D):
    img = image3DToSITK(image)

    extreme_points = [img.TransformIndexToPhysicalPoint(np.array([0, 0, 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([image.gridSize[0], 0, 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([image.gridSize[0], image.gridSize[1], 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([image.gridSize[0], image.gridSize[1], image.gridSize[2]]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([image.gridSize[0], 0, image.gridSize[2]]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([0, image.gridSize[1], 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([0, image.gridSize[1], image.gridSize[2]]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([0, 0, image.gridSize[2]]).astype(int).tolist())]

    return extreme_points

def extremePointsAfterTransform(image:Image3D, tform:np.ndarray,
                                center: Optional[Sequence[float]]=None, translation:Sequence[float]=[0, 0, 0]):
    img = image3DToSITK(image)

    if tform.shape[1] == 4:
        translation = tform[0:-1, -1]
        tform = tform[0:-1, 0:-1]

    dimension = img.GetDimension()

    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(tform.flatten())
    transform.Translate(translation)
    if not (center is None):
        transform.SetCenter(center)

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

def applyTransform(data, tform:np.ndarray, fillValue:float=0., outputBox:Optional[Union[Sequence[float], str]]='keepAll',
    center: Optional[Union[Sequence[float], str]]='imgCenter', translation:Sequence[float]=[0, 0, 0]):

    # print(type(data), data.imageArray.shape, type(tform), tform.shape)
    print('in sitKImageProc applyTransform, center:', center)
    if isinstance(tform, Transform3D):
        tform = tform.tform

    if isinstance(data, Image3D):
        print('in sitKImageProc applyTransform in if instance Image3D')
        if isinstance(data, VectorField3D):
            applyTransformToVectorField(data, tform, fillValue=fillValue, outputBox=outputBox, center=center, translation=translation)
        else:
            applyTransformToImage3D(data, tform, fillValue=fillValue, outputBox=outputBox, center=center, translation=translation)

    if isinstance(data, Dynamic3DSequence):
        for image in data.dyn3DImageList:
            applyTransformToImage3D(image, tform, fillValue=fillValue, outputBox=outputBox, center=center, translation=translation)

    if isinstance(data, Dynamic3DModel):
        applyTransformToImage3D(data.midp, tform, fillValue=fillValue, outputBox=outputBox, center=center, translation=translation)
        for df in data.deformationList:
            applyTransformToVectorField(df, tform, fillValue=fillValue, outputBox=outputBox, center=center, translation=translation)


def applyTransformToImage3D(image:Image3D, tform:np.ndarray, fillValue:float=0., outputBox:Optional[Union[Sequence[float], str]]='keepAll',
    center: Optional[Union[Sequence[float], str]]=None, translation:Sequence[float]=[0, 0, 0]):
    imgType = image.imageArray.dtype

    img = image3DToSITK(image)
    
    if tform.shape[1] == 4:
        translation = tform[0:-1, -1]
        tform = tform[0:-1, 0:-1]
    
    dimension = img.GetDimension()
    
    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(tform.flatten())
    transform.Translate(translation)

    print('center choice ---------------------', center)
    if not (center is None):
        if center == 'dicomCenter':
            print('in elif dicomCenter')
            center = np.array([0, 0, 0])
            transform.SetCenter(center)
        elif len(center) == 3 and (type(center[0]) == float or type(center[0]) == int):
            print('in elif Sequence')
            # center = np.array(center)
            transform.SetCenter(center)
        elif center == 'imgCorner':
            print('in elif imgCorner')
            center = image.origin
            transform.SetCenter(center)
        elif center == 'imgCenter':
            print('in elif imgCenter')
            center = image.origin + image.gridSizeInWorldUnit / 2
            # transform.SetCenter(center)
        else:
            print('Rotation center not recognized, default value is used (image center)')
            center = image.origin + image.gridSizeInWorldUnit / 2
            transform.SetCenter(center)


    if outputBox == 'keepAll':
        min_x, max_x, min_y, max_y, min_z, max_z = extremePointsAfterTransform(image, tform, translation=translation)

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

def applyTransformToVectorField(vectField:VectorField3D, tform:np.ndarray, fillValue:float=0., outputBox:Optional[Union[Sequence[float], str]]='keepAll',
    center: Optional[Union[Sequence[float], str]]='imgCenter', translation:Sequence[float]=[0, 0, 0]):

    print('in sitk image proc, applyTransformToVectorField')

    vectorFieldCompList = []
    for i in range(3):
        compImg = Image3D.fromImage3D(vectField)
        compImg.imageArray = vectField.imageArray[:, :, :, i]
        # import matplotlib.pyplot as plt
        # print(compImg.origin)
        # plt.figure()
        # plt.imshow(compImg.imageArray[:,10,:])
        # plt.show()
        applyTransformToImage3D(compImg, tform, fillValue=fillValue, outputBox=outputBox, center=center, translation=translation)
        # print(compImg.origin)
        # plt.figure()
        # plt.imshow(compImg.imageArray[:, 10, :])
        # plt.show()
        vectorFieldCompList.append(compImg.imageArray)

    vectField.imageArray = np.stack(vectorFieldCompList, axis=3)
    vectField.origin = compImg.origin

    if tform.shape[1] == 4:
        tform = tform[0:-1, 0:-1]

    r = R.from_matrix(tform)

    flattenedVectorField = vectField.imageArray.reshape((vectField.gridSize[0] * vectField.gridSize[1] * vectField.gridSize[2], 3))
    flattenedVectorField = r.apply(flattenedVectorField, inverse=True)

    vectField.imageArray = flattenedVectorField.reshape((vectField.gridSize[0], vectField.gridSize[1], vectField.gridSize[2], 3))


def applyTransformToPoint(tform:np.ndarray, pnt:np.ndarray, center: Optional[Sequence[float]]=None, translation:Sequence[float]=[0, 0, 0]):
    if tform.shape[1] == 4:
        translation = tform[0:-1, -1]
        tform = tform[0:-1, 0:-1]

    transform = sitk.AffineTransform(3)
    transform.SetMatrix(tform.flatten())
    transform.Translate(translation)

    if not (center is None):
        transform.SetCenter(center)

    inv_transform = transform.GetInverse()

    return inv_transform.TransformPoint(pnt.tolist())

def connectComponents(image:Image3D):
    img = image3DToSITK(image, type='uint8')
    return sitkImageToImage3D(sitk.RelabelComponent(sitk.ConnectedComponent(img)))

def rotateImage3DSitk(img3D, rotAngleInDeg, cval=-1000, center='imgCenter'):

    rotAngleInDeg = np.array(rotAngleInDeg)
    rotAngleInRad = -rotAngleInDeg*np.pi/180
    r = R.from_euler('XYZ', rotAngleInRad)

    # print('r.as_matrix()', r.as_matrix())
    # print('r.as_euler()', r.as_euler('zxy'))
    # print('r.as_euler()', r.as_euler('XYZ', degrees=True))
    # print('r.as_euler()', r.as_euler('ZYX'))

    # affTransformMatrix = np.array([[1, 0, 0, 0],
    #                                [0, 1, 0, 0],
    #                                [0, 0, 1, 0],
    #                                [0, 0, 0, 1]]).astype(np.float)
    #
    # affTransformMatrix[0:3, 0:3] = r.as_matrix()
    affTransformMatrix = transform3DMatrixFromTranslationAndRotationsVectors(rotation=rotAngleInDeg)
    applyTransform(img3D, affTransformMatrix, outputBox='same', center=center, fillValue=cval)

def translateImage3DSitk(img3D, translationInMM, cval=-1000):

    # affTransformMatrix = np.array([[1, 0, 0, -translationInMM[0]],
    #                              [0, 1, 0, -translationInMM[1]],
    #                              [0, 0, 1, -translationInMM[2]],
    #                              [0, 0, 0, 1]]).astype(np.float)

    affTransformMatrix = transform3DMatrixFromTranslationAndRotationsVectors(translation=translationInMM)

    applyTransform(img3D, affTransformMatrix, outputBox='same', fillValue=cval)

def register(fixed_image, moving_image, multimodal = True, fillValue:float=0.):
    initial_transform = sitk.CenteredTransformInitializer(fixed_image, moving_image, sitk.Euler3DTransform(), sitk.CenteredTransformInitializerFilter.GEOMETRY)
    
    registration_method = sitk.ImageRegistrationMethod()

    if multimodal:
        registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
        registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
        registration_method.SetMetricSamplingPercentage(0.05, seed=76926294)
    else:
        registration_method.SetMetricAsMeanSquares()
        registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
        registration_method.SetMetricSamplingPercentage(0.05, seed=76926294)

    registration_method.SetOptimizerAsRegularStepGradientDescent(learningRate=1.0, minStep=1e-6, numberOfIterations=1000)
    registration_method.SetOptimizerScalesFromPhysicalShift()

    registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    registration_method.SetInterpolator(sitk.sitkLinear)
    registration_method.SetInitialTransform(initial_transform, inPlace=False)
    
    composite_transform = registration_method.Execute(fixed_image, moving_image)
    moving_resampled = sitk.Resample(moving_image, fixed_image, composite_transform, sitk.sitkLinear, fillValue, moving_image.GetPixelID())

    print('Final metric value: {0}'.format(registration_method.GetMetricValue()))
    print('Optimizer\'s stopping condition, {0}'.format(registration_method.GetOptimizerStopConditionDescription()))

    final_transform = sitk.CompositeTransform(composite_transform).GetBackTransform()
    euler3d_transform = sitk.Euler3DTransform(final_transform)
    euler3d_transform.SetComputeZYX(True)
    tform = np.zeros((4,4))
    tform[0:-1, -1] = euler3d_transform.GetTranslation()
    tform[0:-1, 0:-1] = np.array(euler3d_transform.GetMatrix()).reshape(3,3)
    center = euler3d_transform.GetCenter()

    return tform, center, sitkImageToImage3D(moving_resampled)

def dilate(image:Image3D, radius:Union[float, Sequence[float]]):
    imgType = image.imageArray.dtype

    img = image3DToSITK(image, type=np.int)

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
    resize(imageITK, np.array([0.5, 0.5, 0.5]), newOrigin=imageITK.origin, newShape=imageITK.gridSize*2, fillValue=0.)
    end = time.time()
    print('Simple ITK from shape ' + str(image.gridSize) + ' to shape ' + str(imageITK.gridSize) + ' in '+ str(end - start) + ' s')


    start = time.time()
    imageArrayCupy = resampler3D.resampleOpenMP(image.imageArray, image.origin, image.spacing, image.gridSize,
                                                imageITK.origin, imageITK.spacing, imageITK.gridSize,
                                                fillValue=0, outputType=None, tryGPU=True)
    end = time.time()
    print('Cupy from shape ' + str(image.gridSize) + ' to shape ' + str(imageArrayCupy.shape) + ' in ' + str(end - start) + ' s')

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


