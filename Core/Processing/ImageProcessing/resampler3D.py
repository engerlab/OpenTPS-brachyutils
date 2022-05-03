import numpy as np
import logging

import Core.Processing.ImageProcessing.imageFilter3D as imageFilter3D
from Core.Processing.C_libraries.libInterp3_wrapper import interpolateTrilinear

logger = logging.getLogger(__name__)


def resample(data,inputOrigin,inputSpacing,inputGridSize,outputOrigin,outputSpacing,outputGridSize,fillValue=0,outputType=None, tryGPU=True):

    """Resample 3D data according to new voxel grid using linear interpolation.

    Parameters
    ----------
    data : numpy array
        data to be resampled.
    inputOrigin : list
        origin of the input data voxel grid.
    inputSpacing : list
        spacing of the input data voxel grid.
    inputGridSize : list
        size of the input data voxel grid.
    outputOrigin : list
        origin of the output data voxel grid.
    outputSpacing : list
        spacing of the output data voxel grid.
    outputGridSize : list
        size of the output data voxel grid.
    fillValue : scalar
        interpolation value for locations outside the input voxel grid.
    outputType : numpy data type
        type of the output.

    Returns
    -------
    numpy array
        Resampled data.
    """

    if outputType is None:
        outputType = data.dtype

    vectorDimension = 1
    if data.ndim > 3:
        vectorDimension = data.shape[3]

    # anti-aliasing filter
    sigma = [0, 0, 0]
    if (outputSpacing[0] > inputSpacing[0]): sigma[0] = 0.4 * (outputSpacing[0] / inputSpacing[0])
    if (outputSpacing[1] > inputSpacing[1]): sigma[1] = 0.4 * (outputSpacing[1] / inputSpacing[1])
    if (outputSpacing[2] > inputSpacing[2]): sigma[2] = 0.4 * (outputSpacing[2] / inputSpacing[2])
    if (sigma != [0, 0, 0]):
        logger.info("Data is filtered before downsampling")
        if vectorDimension > 1:
            for i in range(vectorDimension):
                data[:, :, :, i] = imageFilter3D.gaussConv(data[:, :, :, i], sigma, tryGPU=tryGPU)
        else:
            data[:, :, :] = imageFilter3D.gaussConv(data[:, :, :], sigma, tryGPU=tryGPU)

    interpX = (outputOrigin[0] - inputOrigin[0] + np.arange(outputGridSize[0]) * outputSpacing[0]) / inputSpacing[0]
    interpY = (outputOrigin[1] - inputOrigin[1] + np.arange(outputGridSize[1]) * outputSpacing[1]) / inputSpacing[1]
    interpZ = (outputOrigin[2] - inputOrigin[2] + np.arange(outputGridSize[2]) * outputSpacing[2]) / inputSpacing[2]

    # Correct for potential precision issues on the border of the grid
    interpX[interpX > inputGridSize[0] - 1] = np.round(interpX[interpX > inputGridSize[0] - 1] * 1e3) / 1e3
    interpY[interpY > inputGridSize[1] - 1] = np.round(interpY[interpY > inputGridSize[1] - 1] * 1e3) / 1e3
    interpZ[interpZ > inputGridSize[2] - 1] = np.round(interpZ[interpZ > inputGridSize[2] - 1] * 1e3) / 1e3

    xi = np.array(np.meshgrid(interpX, interpY, interpZ))
    xi = np.rollaxis(xi, 0, 4)
    xi = xi.reshape((xi.size // 3, 3))

    if vectorDimension > 1:
        field = np.zeros((*outputGridSize, vectorDimension))
        for i in range(vectorDimension):
            fieldTemp = interpolateTrilinear(data[:, :, :, i], inputGridSize, xi, fillValue=fillValue, tryGPU=tryGPU)
            field[:, :, :, i] = fieldTemp.reshape((outputGridSize[1], outputGridSize[0], outputGridSize[2])).transpose(1, 0, 2)
        data = field
    else:
        data = interpolateTrilinear(data, inputGridSize, xi, fillValue=fillValue, tryGPU=tryGPU)
        data = data.reshape((outputGridSize[1], outputGridSize[0], outputGridSize[2])).transpose(1, 0, 2)

    return data.astype(outputType)

def warp(data,field,spacing,fillValue=0,outputType=None, tryGPU=True):

    """Warp 3D data based on 3D vector field using linear interpolation.

    Parameters
    ----------
    data : numpy array
        data to be warped.
    field : numpy array
        origin of the input data voxel grid.
    spacing : list
        spacing of the input data voxel grid.
    fillValue : scalar
        interpolation value for locations outside the input voxel grid.
    outputType : numpy data type
        type of the output.

    Returns
    -------
    numpy array
        Warped data.
    """

    if outputType is None:
        outputType = data.dtype
    size = data.shape

    if (field.shape[0:3] != size):
        logger.error("Image dimensions must match with the vector field to apply the displacement field.")
        return

    x = np.arange(size[0])
    y = np.arange(size[1])
    z = np.arange(size[2])
    xi = np.array(np.meshgrid(x, y, z))
    xi = np.rollaxis(xi, 0, 4)
    xi = xi.reshape((xi.size // 3, 3))
    xi = xi.astype('float32')
    xi[:, 0] += field[:, :, :, 0].transpose(1, 0, 2).reshape((xi.shape[0],)) / spacing[0]
    xi[:, 1] += field[:, :, :, 1].transpose(1, 0, 2).reshape((xi.shape[0],)) / spacing[1]
    xi[:, 2] += field[:, :, :, 2].transpose(1, 0, 2).reshape((xi.shape[0],)) / spacing[2]
    if fillValue == 'closest':
        xi[:, 0] = np.maximum(np.minimum(xi[:, 0], size[0] - 1), 0)
        xi[:, 1] = np.maximum(np.minimum(xi[:, 1], size[1] - 1), 0)
        xi[:, 2] = np.maximum(np.minimum(xi[:, 2], size[2] - 1), 0)
        fillValue = -1000
    output = interpolateTrilinear(data, size, xi, fillValue=fillValue, tryGPU=tryGPU)
    output = output.reshape((size[1], size[0], size[2])).transpose(1, 0, 2)

    return output.astype(outputType)
