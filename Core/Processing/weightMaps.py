import numpy as np
from scipy.interpolate import LinearNDInterpolator, interpn
from Core.Data.Images.image3D import Image3D
import time
import matplotlib.pyplot as plt


def createExternalPoints(imgSize, numberOfPointsPerEdge = 0):
    """

    """
    xHalfSize = imgSize[0] / 2
    yHalfSize = imgSize[1] / 2
    zHalfSize = imgSize[2] / 2
    externalPoints = []

    if numberOfPointsPerEdge <= 1:
        externalPoints += [[-xHalfSize, -yHalfSize, -zHalfSize],
                          [imgSize[0] + xHalfSize, -yHalfSize, -zHalfSize],
                          [imgSize[0] + xHalfSize, -yHalfSize, imgSize[2] + zHalfSize],
                          [-xHalfSize, -yHalfSize, imgSize[2] + zHalfSize],
                          [-xHalfSize, imgSize[1] + yHalfSize, -zHalfSize],
                          [imgSize[0] + xHalfSize, imgSize[1] + yHalfSize, -zHalfSize],
                          [imgSize[0] + xHalfSize, imgSize[1] + yHalfSize, imgSize[2] + zHalfSize],
                          [-xHalfSize, imgSize[1] + yHalfSize, imgSize[2] + zHalfSize]]

    if numberOfPointsPerEdge == 1:
        externalPoints += [[xHalfSize, imgSize[1] + yHalfSize, zHalfSize],
                          [xHalfSize, -yHalfSize, zHalfSize],
                          [imgSize[0] + xHalfSize, yHalfSize, zHalfSize],
                          [-xHalfSize, yHalfSize, zHalfSize],
                          [xHalfSize, yHalfSize, imgSize[2] + zHalfSize],
                          [xHalfSize, yHalfSize, -zHalfSize]]

    elif numberOfPointsPerEdge > 2:
        print('in elif')
        ## in Z
        dim1 = np.linspace(-xHalfSize, imgSize[0] + xHalfSize, numberOfPointsPerEdge)
        dim2 = np.linspace(-yHalfSize, imgSize[1] + yHalfSize, numberOfPointsPerEdge)

        dim1, dim2 = np.meshgrid(dim1, dim2)
        coordinate_grid = np.array([dim1, dim2])
        coordinate_grid = coordinate_grid.transpose(1, 2, 0)

        for i in range(coordinate_grid.shape[0]):
            for j in range(coordinate_grid.shape[1]):
                externalPoints.append([coordinate_grid[i, j][0], coordinate_grid[i, j][1], -zHalfSize])
                externalPoints.append([coordinate_grid[i, j][0], coordinate_grid[i, j][1], imgSize[2] + zHalfSize])


        ## in X
        dim1 = np.linspace(-zHalfSize, imgSize[2] + zHalfSize, numberOfPointsPerEdge)
        dim2 = np.linspace(-yHalfSize, imgSize[1] + yHalfSize, numberOfPointsPerEdge)

        dim1, dim2 = np.meshgrid(dim1, dim2)
        coordinate_grid = np.array([dim1, dim2])
        coordinate_grid = coordinate_grid.transpose(1, 2, 0)

        for i in range(coordinate_grid.shape[0]):
            for j in range(coordinate_grid.shape[1]):
                externalPoints.append([-xHalfSize, coordinate_grid[i, j][1], coordinate_grid[i, j][0]])
                externalPoints.append([imgSize[0] + xHalfSize, coordinate_grid[i, j][1], coordinate_grid[i, j][0], ])
        #
        #
        # in Y
        dim1 = np.linspace(-xHalfSize, imgSize[0] + xHalfSize, numberOfPointsPerEdge)
        dim2 = np.linspace(-zHalfSize, imgSize[2] + zHalfSize, numberOfPointsPerEdge)

        dim1, dim2 = np.meshgrid(dim1, dim2)
        coordinate_grid = np.array([dim1, dim2])
        coordinate_grid = coordinate_grid.transpose(1, 2, 0)

        for i in range(coordinate_grid.shape[0]):
            for j in range(coordinate_grid.shape[1]):
                externalPoints.append([coordinate_grid[i, j][0], -yHalfSize, coordinate_grid[i, j][1]])
                externalPoints.append([coordinate_grid[i, j][0], imgSize[1] + yHalfSize, coordinate_grid[i, j][1]])


    externalPoints = sorted(externalPoints, key=lambda tup: (tup[0], tup[1], tup[2]))
    checkedIndex = len(externalPoints)-1
    while checkedIndex > 0:
        if externalPoints[checkedIndex][0] == externalPoints[checkedIndex - 1][0] and externalPoints[checkedIndex][1] == externalPoints[checkedIndex - 1][1] and externalPoints[checkedIndex][2] == externalPoints[checkedIndex - 1][2]:
            del externalPoints[checkedIndex]
        checkedIndex -= 1

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

    externalPoints = createExternalPoints(imageGridSize, numberOfPointsPerEdge=5)

    showPoints(externalPoints)

    pointList = externalPoints + internalPoints
    externalValues = np.ones(len(externalPoints))/len(internalPoints)

    weightMapList = []

    for pointIndex in range(len(internalPoints)):
        startTime = time.time()

        internalValues = np.zeros(len(internalPoints))
        internalValues[pointIndex] = 1
        values = np.concatenate((externalValues, internalValues))

        interp = LinearNDInterpolator(pointList, values)
        weightMap = interp(X, Y, Z)

        stopTime = time.time()
        weightMapList.append(weightMap)
        print(pointIndex, 'weight map creation duration', stopTime-startTime)

    return weightMapList


def getWeightMapsAsImage3DList(internalPoints, ref3DImage):
    """

    """
    weightMapList = createWeightMaps(internalPoints, ref3DImage.gridSize, ref3DImage.origin, ref3DImage.spacing)
    image3DList = []
    for weightMapIndex, weightMap in enumerate(weightMapList):
        image3DList.append(Image3D(imageArray=weightMap, name='weightMap_'+str(weightMapIndex+1), origin=ref3DImage.origin, spacing=ref3DImage.spacing, angles=ref3DImage.angles))

    return image3DList

def showPoints(pointList):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    for point in pointList:
        ax.scatter(point[0], point[1], point[2])

    ax.set_xlabel('X Label')
    ax.set_ylabel('Y Label')
    ax.set_zlabel('Z Label')

    plt.show()