import numpy as np
from scipy.interpolate import LinearNDInterpolator
from Core.Data.Images.image3D import Image3D
import time


def createExternalPoints(imgSize):
    """

    """
    xHalfSize = imgSize[0] / 2
    yHalfSize = imgSize[1] / 2
    zHalfSize = imgSize[2] / 2

    externalPoints = [[-xHalfSize, -yHalfSize, -zHalfSize],
                      [imgSize[0] + xHalfSize, -yHalfSize, -zHalfSize],
                      [imgSize[0] + xHalfSize, -yHalfSize, imgSize[2] + zHalfSize],
                      [-xHalfSize, -yHalfSize, imgSize[2] + zHalfSize],
                      [-xHalfSize, imgSize[1] + yHalfSize, -zHalfSize],
                      [imgSize[0] + xHalfSize, imgSize[1] + yHalfSize, -zHalfSize],
                      [imgSize[0] + xHalfSize, imgSize[1] + yHalfSize, imgSize[2] + zHalfSize],
                      [-xHalfSize, imgSize[1] + yHalfSize, imgSize[2] + zHalfSize]]

    return externalPoints


def createWeightMaps(internalPoints, imageGridSize, imageOrigin, pixelSpacing):
    """

    """
    ## get points coordinates in voxels (no need to get them in int, it will not be used to access image values)
    for pointIndex in range(len(internalPoints)):
        for i in range(3):
            internalPoints[pointIndex][i] = (internalPoints[pointIndex][i] - imageOrigin[i]) / pixelSpacing[i]

    X = np.linspace(0, imageGridSize[0] - 1, imageGridSize[0])
    Y = np.linspace(0, imageGridSize[1] - 1, imageGridSize[1])
    Z = np.linspace(0, imageGridSize[2] - 1, imageGridSize[2])

    X, Y, Z = np.meshgrid(X, Y, Z, indexing='ij')  # 3D grid for interpolation

    externalPoints = createExternalPoints(imageGridSize)

    pointList = externalPoints + internalPoints
    externalValues = np.ones(8)/len(internalPoints)

    weightMapList = []

    for pointIndex in range(len(internalPoints)):
        # startTime = time.time()

        internalValues = np.zeros(len(internalPoints))
        internalValues[pointIndex] = 1
        values = np.concatenate((externalValues, internalValues))

        interp = LinearNDInterpolator(pointList, values)
        weightMap = interp(X, Y, Z)
        # stopTime = time.time()
        weightMapList.append(weightMap)
        # print(stopTime-startTime)

    return weightMapList


def getWeightMapsAsImage3DList(internalPoints, ref3DImage):
    """

    """
    weightMapList = createWeightMaps(internalPoints, ref3DImage.gridSize, ref3DImage.origin, ref3DImage.spacing)
    image3DList = []
    for weightMapIndex, weightMap in enumerate(weightMapList):
        image3DList.append(Image3D(imageArray=weightMap, name='weightMap_'+str(weightMapIndex+1), origin=ref3DImage.origin, spacing=ref3DImage.spacing, angles=ref3DImage.angles))

    return image3DList
