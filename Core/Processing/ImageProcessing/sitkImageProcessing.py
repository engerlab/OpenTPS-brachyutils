from typing import Sequence, Optional

import numpy as np

from Core.Data.Images.image3D import Image3D
try:
    import SimpleITK as sitk
except:
    print('No module SimpleITK found')

def image3DToSITK(image:Image3D, type=float):
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
    if newOrigin is None:
        newOrigin = image.origin

    if newShape is None:
        newShape = (image.origin - newOrigin + image.gridSize*image.spacing)/newSpacing
    newShape = np.ceil(newShape).astype(int)

    imgType = image.imageArray.dtype
    img = image3DToSITK(image)

    dimension = img.GetDimension()

    reference_image = sitk.Image(newShape.tolist(), img.GetPixelIDValue())
    reference_image.SetOrigin(newOrigin.tolist())
    reference_image.SetSpacing(newSpacing.tolist())
    reference_image.SetDirection(img.GetDirection())

    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(img.GetDirection())

    outImg = sitk.Resample(img, reference_image, transform, sitk.sitkLinear, fillValue)
    outData = np.array(sitk.GetArrayFromImage(outImg)).astype(imgType)

    outData = np.swapaxes(outData, 0, 2)

    image.imageArray = outData
    image.origin = newOrigin
    image.spacing = newSpacing

def applyTransform(image:Image3D, tform:np.ndarray, fillValue:float=0.):
    img = image3DToSITK(image)
    tform = tform[0:-1, 0:-1]

    dimension = img.GetDimension()

    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(tform.flatten())

    extreme_points = [img.TransformIndexToPhysicalPoint(np.array([0, 0, 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([image.gridSize[0], 0, 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([image.gridSize[0], image.gridSize[1], 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([image.gridSize[0], image.gridSize[1], image.gridSize[2]]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([image.gridSize[0], 0, image.gridSize[2]]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([0, image.gridSize[1], 0]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([0, image.gridSize[1], image.gridSize[2]]).astype(int).tolist()),
                      img.TransformIndexToPhysicalPoint(np.array([0, 0, image.gridSize[2]]).astype(int).tolist())]

    inv_transform = transform.GetInverse()

    extreme_points_transformed = [inv_transform.TransformPoint(pnt) for pnt in extreme_points]
    min_x = min(extreme_points_transformed)[0]
    min_y = min(extreme_points_transformed, key=lambda p: p[1])[1]
    min_z = min(extreme_points_transformed, key=lambda p: p[2])[2]
    max_x = max(extreme_points_transformed)[0]
    max_y = max(extreme_points_transformed, key=lambda p: p[1])[1]
    max_z = max(extreme_points_transformed, key=lambda p: p[2])[2]

    output_origin = [min_x, min_y, min_z]
    output_size = [int((max_x - min_x) / image.spacing[0]), int((max_y - min_y) / image.spacing[1]), int((max_z - min_z) / image.spacing[1])]

    reference_image = sitk.Image(output_size, img.GetPixelIDValue())
    reference_image.SetOrigin(output_origin)
    reference_image.SetSpacing(image.spacing.tolist())
    reference_image.SetDirection(img.GetDirection())

    outImg = sitk.Resample(img, reference_image, transform, sitk.sitkLinear, fillValue)

    outData = np.array(sitk.GetArrayFromImage(outImg))

    outData = np.swapaxes(outData, 0, 2)

    image.imageArray = outData
    image.origin = output_origin

def applyTransformToPoint(tform:np.ndarray, pnt:np.ndarray):
    tform = tform[0:-1, 0:-1]

    transform = sitk.AffineTransform(3)
    transform.SetMatrix(tform.flatten())

    inv_transform = transform.GetInverse()

    return inv_transform.TransformPoint(pnt.tolist())

def connectComponents(image:Image3D):
    img = image3DToSITK(image, type='uint8')
    return sitkImageToImage3D(sitk.RelabelComponent(sitk.ConnectedComponent(img)))
