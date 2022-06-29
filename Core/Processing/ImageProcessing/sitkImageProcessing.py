
import time
from typing import Optional, Sequence, Union

import numpy as np
from scipy.spatial.transform import Rotation as R
from Core.Data.Images.vectorField3D import VectorField3D

try:
    import SimpleITK as sitk
except:
    print('No module SimpleITK found')

from Core.Processing.ImageProcessing import resampler3D
from Core.Data.Images.image3D import Image3D


def image3DToSITK(image:Image3D, type=np.float32):
    imageData = image.imageArray.astype(type)

    print('in image3DToSITK before swap axis image.imageArray.shape', image.imageArray.shape)
    imageData = np.swapaxes(imageData, 0, 2)

    if isinstance(image, VectorField3D):
        img = []
        for i in range(3):
            img.append(sitk.GetImageFromArray(imageData[:, :, :, i].astype(type)))
            img[-1].SetOrigin(image.origin.tolist())
            img[-1].SetSpacing(image.origin.tolist())
            
    else:
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

    if newShape is None:
        newShape = (image.origin - newOrigin + image.gridSize*image.spacing)/newSpacing
    newShape = np.ceil(newShape).astype(int)

    imgType = image.imageArray.dtype
    img = image3DToSITK(image)
    if isinstance(image, VectorField3D):
        dimension = img[0].GetDimension()
        reference_image = sitk.Image(newShape.tolist(), img[0].GetPixelIDValue())
        reference_image.SetDirection(img[0].GetDirection())
    else:
        dimension = img.GetDimension()
        reference_image = sitk.Image(newShape.tolist(), img.GetPixelIDValue())
        reference_image.SetDirection(img.GetDirection())
    # print('in sitkImageProcessing resize', dimension)
    # reference_image = sitk.Image(newShape.tolist(), img.GetPixelIDValue())
    reference_image.SetOrigin(newOrigin.tolist())
    reference_image.SetSpacing(newSpacing.tolist())
    

    transform = sitk.AffineTransform(dimension)
    if isinstance(image, VectorField3D):
        transform.SetMatrix(img[0].GetDirection())
    else:
        transform.SetMatrix(img.GetDirection())

    if isinstance(image, VectorField3D):
        outImg1 = sitk.Resample(img[0], reference_image, transform, sitk.sitkLinear, fillValue)
        outImg2 = sitk.Resample(img[1], reference_image, transform, sitk.sitkLinear, fillValue)
        outImg3 = sitk.Resample(img[2], reference_image, transform, sitk.sitkLinear, fillValue)
        outData1 = np.array(sitk.GetArrayFromImage(outImg1))
        outData2 = np.array(sitk.GetArrayFromImage(outImg2))
        outData3 = np.array(sitk.GetArrayFromImage(outImg3))
        print('in sitk image proc resize last isinstance')
        print(outData1.shape, outData2.shape, outData3.shape)
        outData = np.stack((outData1, outData2, outData3),  axis=3)
        # np.stack(arrays, axis=0)
    else:  
        outImg = sitk.Resample(img, reference_image, transform, sitk.sitkLinear, fillValue)
        outData = np.array(sitk.GetArrayFromImage(outImg))

    if imgType==bool:
        outData[outData<0.5] = 0
    outData = outData.astype(imgType)

    outData = np.swapaxes(outData, 0, 2)

    image.imageArray = outData
    print('in sitk image proc resize end image.imageArray.shape', image.imageArray.shape)
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
                                centre: Optional[Sequence[float]]=None, translation:Sequence[float]=[0, 0, 0]):
    img = image3DToSITK(image)

    if tform.shape[1] == 4:
        translation = tform[0:-1, -1]
        tform = tform[0:-1, 0:-1]

    dimension = img.GetDimension()

    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(tform.flatten())
    transform.Translate(translation)
    if not (centre is None):
        transform.SetCenter(centre)

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

def applyTransform(image:Image3D, tform:np.ndarray, fillValue:float=0., outputBox:Optional[Union[Sequence[float], str]]='keepAll',
    centre: Optional[Sequence[float]]=None, translation:Sequence[float]=[0, 0, 0]):
    imgType = image.imageArray.dtype

    img = image3DToSITK(image)
    if tform.shape[1] == 4:
        translation = tform[0:-1, -1]
        tform = tform[0:-1, 0:-1]

    dimension = img.GetDimension()

    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(tform.flatten())
    transform.Translate(translation)

    if not (centre is None):
        transform.SetCenter(centre)

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
    if imgType==bool:
        outData[outData<0.5] = 0
    outData = outData.astype(imgType)

    outData = np.swapaxes(outData, 0, 2)

    image.imageArray = outData
    image.origin = output_origin

def applyTransformToPoint(tform:np.ndarray, pnt:np.ndarray, centre: Optional[Sequence[float]]=None, translation:Sequence[float]=[0, 0, 0]):
    if tform.shape[1] == 4:
        translation = tform[0:-1, -1]
        tform = tform[0:-1, 0:-1]

    transform = sitk.AffineTransform(3)
    transform.SetMatrix(tform.flatten())
    transform.Translate(translation)

    if not (centre is None):
        transform.SetCenter(centre)

    inv_transform = transform.GetInverse()

    return inv_transform.TransformPoint(pnt.tolist())

def connectComponents(image:Image3D):
    img = image3DToSITK(image, type='uint8')
    return sitkImageToImage3D(sitk.RelabelComponent(sitk.ConnectedComponent(img)))

def rotateImage3DSitk(img3D, rotAngleInDeg=0, rotAxis=0, cval=-1000):

    r = R.from_rotvec(rotAngleInDeg * np.roll(np.array([1, 0, 0]), rotAxis), degrees=True)
    imgCenter = img3D.origin + img3D.gridSizeInWorldUnit / 2

    applyTransform(img3D, r.as_matrix(), outputBox='same', centre=imgCenter, fillValue=cval)



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


