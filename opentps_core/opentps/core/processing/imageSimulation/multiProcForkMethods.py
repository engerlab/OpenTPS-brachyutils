import numpy as np
import time
import concurrent
import logging 

from opentps.core.processing.imageSimulation.DRRToolBox import forwardProjection
from opentps.core.processing.imageProcessing.image2DManip import getBinaryMaskFromROIDRR, get2DMaskCenterOfMass

logger = logging.getLogger(__name__)
def multiProcDRRs(dataList, projAngle, projAxis, outputSize, ncore=None):
    """
    This function is used to generate DRRs from a list of images and masks.
    It uses multiprocessing to speed up the process.

    Parameters
    ----------
    dataList : list
        List of images and masks. Each element of the list is a list of two elements: image and mask.
    projAngle : float
        Projection angle in degrees.
    projAxis : str
        Projection axis. Can be 'X', 'Y' or 'Z'.
    outputSize : list
        Output size of the DRRs. It is a list of two elements: number of rows and number of columns.
    ncore : int, optional
        Number of cores used for multiprocessing. If None, all the logical cores of the machine are used. The default is None.

    Returns
    -------
    croppedImgAndMaskDRRsPlus2DCOM : list
        List of DRRs, masks and 2D center of mass. Each element of the list is a list of three elements: DRR, mask and 2D center of mass.
    """

    import multiprocessing
    multiprocessing.set_start_method('fork', force=True)

    imgList = [dataList[i][0] for i in range(len(dataList))]
    maskList = [dataList[i][1] for i in range(len(dataList))]
    projAngleList = [projAngle for i in range(len(dataList))]
    projAxisList = [projAxis for i in range(len(dataList))]
    outputSizeList = [outputSize for i in range(len(dataList))]
    
    nbrCore = multiprocessing.cpu_count() #number of logical cores of the machine
    croppedImgAndMaskDRRsPlus2DCOM = []
    if ncore == None: 
        logger.info("Number of logical cores used: %d", nbrCore)      
        with concurrent.futures.ProcessPoolExecutor() as executor:
            croppedImgAndMaskDRRsPlus2DCOM = executor.map(DRRsBinarizeAndCrop, imgList, maskList, projAngleList, projAxisList, outputSizeList)
        executor.shutdown(wait=False)
        
    elif ncore <= nbrCore: 
        logger.info("Number of logical cores used: %d", ncore)      
        with concurrent.futures.ProcessPoolExecutor(max_workers=ncore) as executor:
            results = executor.map(DRRsBinarizeAndCrop, imgList, maskList, projAngleList, projAxisList, outputSizeList)
            croppedImgAndMaskDRRsPlus2DCOM += results
        executor.shutdown(wait=False)
        
    else:
        logger.error("Too many cores asked. The machine has less logical cores.")
        
    # for element in dataList:
    #     croppedImgAndMaskDRRsPlus2DCOM.append(DRRsBinarizeAndCrop(element[0], element[1], projectionAngle=projAngle, projectionAxis=projAxis, outputSize=outputSize))
    
    return croppedImgAndMaskDRRsPlus2DCOM

## ------------------------------------------------------------------------------------
def DRRsBinarizeAndCrop(image, mask, projectionAngle=0, projectionAxis='Z', outputSize=[]):
    """
    This function is used to generate a DRR from an image and a mask. It also crops the DRR to remove the black borders.

    Parameters
    ----------
    image : numpy array
        Image.
    mask : numpy array
        Mask.
    projectionAngle : float, optional
        Projection angle in degrees. The default is 0.
    projectionAxis : str, optional
        Projection axis. Can be 'X', 'Y' or 'Z'. The default is 'Z'.
    outputSize : list, optional
        Output size of the DRR. It is a list of two elements: number of rows and number of columns. The default is [].

    Returns
    -------
    list
        List of DRR, mask and 2D center of mass. Each element of the list is a list of three elements: DRR, mask and 2D center of mass.
    """
    
    startTime = time.time()
    DRR = forwardProjection(image, projectionAngle, axis=projectionAxis)
    DRRMask = forwardProjection(mask, projectionAngle, axis=projectionAxis)

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
    logger.info(f'DRR projection done in {time.time() - startTime}')
    return [DRR, binaryDRRMask, centerOfMass]

## ------------------------------------------------------------------------------------