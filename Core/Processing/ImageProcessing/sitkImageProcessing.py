from typing import Sequence, Optional

import numpy as np

from Core.Data.Images.image3D import Image3D
import SimpleITK as sitk

def image3DToSITK(image:Image3D):
    imageData = image.imageArray.astype(float) #np.swapaxes(image.imageArray, 0, 2)
    img = sitk.GetImageFromArray(imageData)

    img.SetOrigin(image.origin.tolist())
    img.SetSpacing(image.spacing.tolist())
    # TODO SetDirection from angles but it is not clear how angles is defined

    return img

def resize(image:Image3D, newSpacing:np.ndarray, newOirigin:Optional[np.ndarray]=None, newShape:Optional[np.ndarray]=None, fillValue:float=0.):
    if newOirigin is None:
        newOirigin = image.origin

    if newShape is None:
        newShape = (image.origin - newOirigin + image.gridSize*image.spacing)/newSpacing
    newShape = np.ceil(newShape).astype(int)

    imgType = image.imageArray.dtype
    img = image3DToSITK(image)

    dimension = img.GetDimension()

    reference_image = sitk.Image(newShape.tolist(), img.GetPixelIDValue())
    reference_image.SetOrigin(newOirigin.tolist())
    reference_image.SetSpacing(newSpacing.tolist())
    reference_image.SetDirection(img.GetDirection())

    transform = sitk.AffineTransform(dimension)
    transform.SetMatrix(img.GetDirection())

    outImg = sitk.Resample(img, reference_image, transform, sitk.sitkLinear, fillValue)
    outData = np.array(sitk.GetArrayFromImage(outImg)).astype(imgType)

    #outData = np.swapaxes(outData, 0, 2)

    image.imageArray = outData
    image.origin = newOirigin
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

    # outData = np.swapaxes(outData, 0, 2)

    image.imageArray = outData
    image.origin = output_origin
