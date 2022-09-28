import numpy as np
import concurrent

from opentps.core.processing.imageSimulation.DRRToolBox import forwardProjection
from opentps.core.processing.imageProcessing.image2DManip import getBinaryMaskFromROIDRR, get2DMaskCenterOfMass


def multiProcDRRs(dataList, projAngle, projAxis, outputSize):

    import multiprocessing
    multiprocessing.set_start_method('fork', force=True)

    imgList = [dataList[i][0] for i in range(len(dataList))]
    maskList = [dataList[i][1] for i in range(len(dataList))]
    projAngleList = [projAngle for i in range(len(dataList))]
    projAxisList = [projAxis for i in range(len(dataList))]
    outputSizeList = [outputSize for i in range(len(dataList))]
    
    croppedImgAndMaskDRRsPlus2DCOM = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        croppedImgAndMaskDRRsPlus2DCOM = executor.map(DRRsBinarizeAndCrop, imgList, maskList, projAngleList, projAxisList, outputSizeList)

    # for element in dataList:
    #     croppedImgAndMaskDRRsPlus2DCOM.append(DRRsBinarizeAndCrop(element[0], element[1], projectionAngle=projAngle, projectionAxis=projAxis, outputSize=outputSize))

    return croppedImgAndMaskDRRsPlus2DCOM

## ------------------------------------------------------------------------------------
def DRRsBinarizeAndCrop(image, mask, projectionAngle=0, projectionAxis='Z', outputSize=[]):

    # startTime = time.time()
    DRR = forwardProjection(image, projectionAngle, axis=projectionAxis)
    # print('DRRs for image created in', time.time() - startTime)
    # startTime = time.time()
    DRRMask = forwardProjection(mask, projectionAngle, axis=projectionAxis)
    # print('DRRs for mask created in', time.time() - startTime)

    rowsToRemove = []
    for i in range(DRR.shape[0]):
        if np.std(DRR[i, :]) == 0:
            rowsToRemove.append(i)

    if rowsToRemove:
        rowsToRemove.reverse
        DRR = np.delete(DRR, rowsToRemove, 0)
        DRRMask = np.delete(DRRMask, rowsToRemove, 0)

    columnsToRemove = []
    for i in range(DRR.shape[1]):
        if np.std(DRR[:, i]) == 0:
            columnsToRemove.append(i)

    if columnsToRemove:
        columnsToRemove.reverse
        DRR = np.delete(DRR, columnsToRemove, 1)
        DRRMask = np.delete(DRRMask, columnsToRemove, 1)
    
    #if outputSize:
        # print('Before resampling')
        # print(DRR.shape, np.min(DRR), np.max(DRR), np.mean(DRR))
        #ratio = [outputSize[0] / DRR.shape[0], outputSize[1] / DRR.shape[1]]
        #DRR = zoom(DRR, ratio)
        #DRRMask = zoom(DRRMask, ratio)
        # print('After resampling')
        # print(DRR.shape, np.min(DRR), np.max(DRR), np.mean(DRR))

    binaryDRRMask = getBinaryMaskFromROIDRR(DRRMask)
    centerOfMass = get2DMaskCenterOfMass(binaryDRRMask)

    del image  # to release the RAM
    del mask  # to release the RAM

    # return [DRR, DRRMask]
    return [DRR, binaryDRRMask, centerOfMass]

## ------------------------------------------------------------------------------------