import numpy as np

import matplotlib.pyplot as plt
from scipy.interpolate import LinearNDInterpolator
import copy
import logging
from opentps.core.data.images._image3D import Image3D

logger = logging.getLogger(__name__)

def createExternalPoints(imgSize, numberOfPointsPerEdge = 0):
    """
    Create a list of points that are outside the image, to be used for the weight maps

    parameters
    ----------
    imgSize : list
        size of the image
    numberOfPointsPerEdge : int
        number of points to create per edge of the image. default is 0, which means no points are created.

    returns
    -------
    externalPoints : list
        list of points that are outside the image
    """
    xHalfSize = imgSize[0] / 2
    yHalfSize = imgSize[1] / 2
    zHalfSize = imgSize[2] / 2

    externalPoints = []

    if numberOfPointsPerEdge < 2:
        numberOfPointsPerEdge = 2

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


    ## remove duplicate points
    externalPoints = sorted(externalPoints, key=lambda tup: (tup[0], tup[1], tup[2]))
    checkedIndex = len(externalPoints)-1
    while checkedIndex > 0:
        if externalPoints[checkedIndex][0] == externalPoints[checkedIndex - 1][0] and externalPoints[checkedIndex][1] == externalPoints[checkedIndex - 1][1] and externalPoints[checkedIndex][2] == externalPoints[checkedIndex - 1][2]:
            del externalPoints[checkedIndex]
        checkedIndex -= 1

    return externalPoints


def createWeightMaps(absoluteInternalPoints, imageGridSize, imageOrigin, pixelSpacing):
    """
    Create a list of weight maps, one for each internal point. Each weight map is a 3D array of the same size as the image, with values between 0 and 1.
    The value 1 is at the position of the internal point, and the value 0 is at the position of the external points.

    parameters
    ----------
    absoluteInternalPoints : list
        list of internal points coordinates in absolute coordinates
    imageGridSize : list
        size of the image
    imageOrigin : list
        origin of the image
    pixelSpacing : list
        pixel spacing of the image

    returns
    -------
    weightMapList : list
        list of weight maps
    """
    ## get points coordinates in voxels (no need to get them in int, it will not be used to access image values)
    internalPoints = copy.deepcopy(absoluteInternalPoints)
    for pointIndex in range(len(internalPoints)):
        for i in range(3):
            internalPoints[pointIndex][i] = (internalPoints[pointIndex][i] - imageOrigin[i]) / pixelSpacing[i]

    X = np.linspace(0, imageGridSize[0] - 1, imageGridSize[0])
    Y = np.linspace(0, imageGridSize[1] - 1, imageGridSize[1])
    Z = np.linspace(0, imageGridSize[2] - 1, imageGridSize[2])

    X, Y, Z = np.meshgrid(X, Y, Z, indexing='ij')  # 3D grid for interpolation

    externalPoints = createExternalPoints(imageGridSize, numberOfPointsPerEdge=5)

    # showPoints(externalPoints)

    pointList = externalPoints + internalPoints
    externalValues = np.ones(len(externalPoints))/len(internalPoints)

    weightMapList = []

    for pointIndex in range(len(internalPoints)):

        # startTime = time.time()

        internalValues = np.zeros(len(internalPoints))
        internalValues[pointIndex] = 1
        values = np.concatenate((externalValues, internalValues))

        interp = LinearNDInterpolator(pointList, values) # this could be replaced by cupy if GPU acceleration is necessary
        weightMap = interp(X, Y, Z)

        # stopTime = time.time()
        # print(pointIndex, 'weight map creation duration', stopTime-startTime)

        weightMapList.append(weightMap)

    return weightMapList


def getWeightMapsAsImage3DList(internalPoints, ref3DImage):
    """
    Create a list of weight maps, one for each internal point. Each weight map is a 3D array of the same size as the image, with values between 0 and 1.

    parameters
    ----------
    internalPoints : list
        list of internal points coordinates in absolute coordinates
    ref3DImage : Image3D
        reference image

    returns
    -------
    image3DList : list
        list of weight maps as Image3D objects
    """
    weightMapList = createWeightMaps(internalPoints, ref3DImage.gridSize, ref3DImage.origin, ref3DImage.spacing)
    image3DList = []
    for weightMapIndex, weightMap in enumerate(weightMapList):
        image3DList.append(Image3D(imageArray=weightMap, name='weightMap_'+str(weightMapIndex+1), origin=ref3DImage.origin, spacing=ref3DImage.spacing, angles=ref3DImage.angles))

    return image3DList


def showPoints(pointList):
    """
    Show a list of points in a plot.

    parameters
    ----------
    pointList : list
        list of points coordinates
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    for point in pointList:
        ax.scatter(point[0], point[1], point[2])

    ax.set_xlabel('X Label')
    ax.set_ylabel('Y Label')
    ax.set_zlabel('Z Label')

    plt.show()


def generateDeformationFromTrackers(midpModel, phases, amplitudes, internalPoints):
    """
    Generate a deformation field from a list of internal points, phases and amplitudes.

    parameters
    ----------
    midpModel : MidPositionModel
        mid-position model
    phases : list
        list of phases
    amplitudes : list
        list of amplitudes
    internalPoints : list
        list of internal points coordinates in absolute coordinates

    returns
    -------
    field : Image3D
        deformation field
    weightMapList : list
        list of weight maps
    """
    if midpModel.midp is None or midpModel.deformationList is None:
        logger.error(
            'Model is empty. Mid-position image and deformation fields must be computed first using computeMidPositionImage().')
        return
    if len(phases) != len(internalPoints):
        logger.error(
            'The number of phases should be the same as the number of internal points.')
        return
    if len(amplitudes) != len(internalPoints):
        logger.error(
            'The number of amplitudes should be the same as the number of internal points.')
        return

    weightMapList = getWeightMapsAsImage3DList(internalPoints, midpModel.deformationList[0])

    field = generateDeformationFromTrackersAndWeightMaps(midpModel, phases, amplitudes, weightMapList)

    return field, weightMapList


def generateDeformationFromTrackersAndWeightMaps(midpModel, phases, amplitudes, weightMapList):
    """
    generate a deformation field from a list of weight maps, phases and amplitudes.

    parameters
    ----------
    midpModel : MidPositionModel
        mid-position model
    phases : list
        list of phases
    amplitudes : list
        list of amplitudes
    weightMapList : list
        list of weight maps

    returns
    -------
    field : Image3D
        deformation field
    """
    if midpModel.midp is None or midpModel.deformationList is None:
        logger.error(
            'Model is empty. Mid-position image and deformation fields must be computed first using computeMidPositionImage().')
        return
    if len(phases) != len(weightMapList):
        logger.error(
            'The number of phases should be the same as the number of weight maps.')
        return
    if len(amplitudes) != len(weightMapList):
        logger.error(
            'The number of amplitudes should be the same as the number of weight maps.')
        return

    field = midpModel.deformationList[0].copy()
    field.displacement = None
    field.setVelocityArray(field.velocity.imageArray * 0)

    for i in range(len(weightMapList)):

        phase = phases[i] * len(midpModel.deformationList)
        phase1 = np.floor(phase) % len(midpModel.deformationList)
        phase2 = np.ceil(phase) % len(midpModel.deformationList)

        if phase1 == phase2:
            field.setVelocityArrayXYZ(field.velocity.imageArray[:, :, :, 0] + amplitudes[i] * np.multiply(weightMapList[i].imageArray, midpModel.deformationList[int(phase1)].velocity.imageArray[:, :, :, 0]),
                                      field.velocity.imageArray[:, :, :, 1] + amplitudes[i] * np.multiply(weightMapList[i].imageArray, midpModel.deformationList[int(phase1)].velocity.imageArray[:, :, :, 1]),
                                      field.velocity.imageArray[:, :, :, 2] + amplitudes[i] * np.multiply(weightMapList[i].imageArray, midpModel.deformationList[int(phase1)].velocity.imageArray[:, :, :, 2]))
        else:
            w1 = abs(phase - np.ceil(phase))
            w2 = abs(phase - np.floor(phase))
            if abs(w1 + w2 - 1.0) > 1e-6:
                logger.error('Error in phase interpolation.')
                return
            field.setVelocityArrayXYZ(field.velocity.imageArray[:, :, :, 0] + amplitudes[i] * np.multiply(weightMapList[i].imageArray, (w1 * midpModel.deformationList[int(phase1)].velocity.imageArray[:,:,:,0] + w2 * midpModel.deformationList[int(phase2)].velocity.imageArray[:,:,:,0])),
                                      field.velocity.imageArray[:, :, :, 1] + amplitudes[i] * np.multiply(weightMapList[i].imageArray, (w1 * midpModel.deformationList[int(phase1)].velocity.imageArray[:,:,:,1] + w2 * midpModel.deformationList[int(phase2)].velocity.imageArray[:,:,:,1])),
                                      field.velocity.imageArray[:, :, :, 2] + amplitudes[i] * np.multiply(weightMapList[i].imageArray, (w1 * midpModel.deformationList[int(phase1)].velocity.imageArray[:,:,:,2] + w2 * midpModel.deformationList[int(phase2)].velocity.imageArray[:,:,:,2])))

    return field

