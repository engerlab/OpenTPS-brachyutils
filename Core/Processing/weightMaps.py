import numpy as np
from scipy.interpolate import LinearNDInterpolator
import logging
from Core.Data.Images.image3D import Image3D

logger = logging.getLogger(__name__)

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


def createWeightMaps(internalPoints, imageSize):
    """

    """
    X = np.linspace(0, imageSize[0]-1, imageSize[0])
    Y = np.linspace(0, imageSize[1]-1, imageSize[1])
    Z = np.linspace(0, imageSize[2]-1, imageSize[2])

    X, Y, Z = np.meshgrid(Y, X, Z)  # 3D grid for interpolation
    externalPoints = createExternalPoints(imageSize)

    pointList = externalPoints + internalPoints
    externalValues = np.ones(8)/len(internalPoints)

    weightMapList = []

    for pointIndex in range(len(internalPoints)):

        internalValues = np.zeros(len(internalPoints))
        internalValues[pointIndex] = 1
        values = np.concatenate((externalValues, internalValues))

        interp = LinearNDInterpolator(pointList, values)
        weightMap = interp(X, Y, Z)
        weightMapList.append(weightMap)

    return weightMapList


def getWeightMapsAsImage3DList(internalPoints, ref3DImage):
    """

    """
    weightMapList = createWeightMaps(internalPoints, ref3DImage.gridSize)
    image3DList = []
    for weightMapIndex, weightMap in enumerate(weightMapList):
        image3DList.append(Image3D(imageArray=weightMap, name='weightMap_'+str(weightMapIndex+1), origin=ref3DImage.origin, spacing=ref3DImage.spacing, angles=ref3DImage.angles))

    return image3DList


def generateDeformationFromTrackers(midpModel, phases, amplitudes, internalPoints):
    """

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

    weightMaps = getWeightMapsAsImage3DList(internalPoints, midpModel.deformationList[0])

    field = midpModel.deformationList[0].copy()
    field.displacement = None
    field.velocity._imageArray = field.velocity._imageArray*0

    for i in range(len(internalPoints)):

        phase = phases[i]*len(midpModel.deformationList)
        phase1 = np.floor(phase) % len(midpModel.deformationList)
        phase2 = np.ceil(phase) % len(midpModel.deformationList)

        if phase1 == phase2:
            for j in range(3):
                field.velocity._imageArray[:,:,:,j] += amplitudes[i] * np.multiply(weightMaps[i].imageArray,midpModel.deformationList[int(phase1)].velocity.imageArray[:,:,:,j])
        else:
            w1 = abs(phase - np.ceil(phase))
            w2 = abs(phase - np.floor(phase))
            if abs(w1 + w2 - 1.0) > 1e-6:
                logger.error('Error in phase interpolation.')
                return
            for j in range(3):
                field.velocity._imageArray[:,:,:,j] += amplitudes[i] * np.multiply(weightMaps[i].imageArray,(
                            w1 * midpModel.deformationList[int(phase1)].velocity.imageArray[:,:,:,j] + w2 * midpModel.deformationList[
                        int(phase2)].velocity.imageArray[:,:,:,j]))

    return field, weightMaps


def generateDeformationFromTrackersAndWeightMaps(midpModel, phases, amplitudes, weightMapList):
    """

    """
