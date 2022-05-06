import time
# from timeit import repeat
from Core.Processing.DRRToolBox import forwardProjection
from Core.Processing.ImageProcessing.image2DManip import getBinaryMaskFromROIDRR, get2DMaskCenterOfMass
from scipy.ndimage import zoom

# multiprocessing.set_start_method('fork', force=True)
import matplotlib.pyplot as plt
import concurrent


def multiProcDRRs(dataList, projAngle, projAxis, outputSize, savingPath):

    # import multiprocessing
    # multiprocessing.set_start_method('fork', force=True)

    test = []
    for imageAndMaskPair in dataList:
        test.append(DRRsBinarizeAndCrop(imageAndMaskPair[0], imageAndMaskPair[1], savingPath, projectionAngle=projAngle, projectionAxis=projAxis, outputSize=outputSize))

    # savingPathList = [savingPath for i in range(len(dataList))]
    # projAngleList = [projAngle for i in range(len(dataList))]
    # projAxisList = [projAxis for i in range(len(dataList))]
    # outputSizeList = [outputSize for i in range(len(dataList))]

    # for element in dataList:
    #     print(type(element[0]), type(element[1]), type(element[2]))

    # multiprocessing.set_start_method('spawn', force=True)
    
    # with concurrent.futures.ProcessPoolExecutor() as executor:
    #     test2 = executor.map(DRRsBinarizeAndCrop, dataList[:][0], dataList[:][1], savingPathList, projAngleList, projAxisList, outputSizeList)
    #     test += test2

    return test

## ------------------------------------------------------------------------------------
def DRRsBinarizeAndCrop(image, mask, savingPath, projectionAngle=0, projectionAxis='Z', outputSize=[]):

    startTime = time.time()
    DRR = forwardProjection(image, projectionAngle, axis=projectionAxis)
    print('DRRs for image created in', time.time() - startTime)
    startTime = time.time()
    DRRMask = forwardProjection(mask, projectionAngle, axis=projectionAxis)
    print('DRRs for mask created in', time.time() - startTime)

    # startTime = time.time()
    halfDiff = int((DRR.shape[1] - image.gridSize[2]) / 2)  ## not sure this will work if orientation is changed
    croppedDRR = DRR[:, halfDiff + 1:DRR.shape[1] - halfDiff - 1]  ## not sure this will work if orientation is changed
    croppedDRRMask = DRRMask[:, halfDiff + 1:DRRMask.shape[1] - halfDiff - 1]  ## not sure this will work if orientation is changed

    if outputSize:
        # print('Before resampling')
        # print(croppedDRR.shape, np.min(croppedDRR), np.max(croppedDRR), np.mean(croppedDRR))
        ratio = [outputSize[0] / croppedDRR.shape[0], outputSize[1] / croppedDRR.shape[1]]
        croppedDRR = zoom(croppedDRR, ratio)
        croppedDRRMask = zoom(croppedDRRMask, ratio)
        # print('After resampling')
        # print(croppedDRR.shape, np.min(croppedDRR), np.max(croppedDRR), np.mean(croppedDRR))

    binaryDRRMask = getBinaryMaskFromROIDRR(croppedDRRMask)
    centerOfMass = get2DMaskCenterOfMass(binaryDRRMask)
    # print('CenterOfMass:', centerOfMass)

    # print('rest computed in', time.time() - startTime)

    del image  # to release the RAM
    del mask  # to release the RAM

    # plt.figure()
    # plt.subplot(1, 5, 1)
    # plt.imshow(DRR)
    # plt.subplot(1, 5, 2)
    # plt.imshow(croppedDRR)
    # plt.subplot(1, 5, 3)
    # plt.imshow(DRRMask)
    # plt.subplot(1, 5, 4)
    # plt.imshow(croppedDRRMask)
    # plt.subplot(1, 5, 5)
    # plt.imshow(binaryDRRMask)
    # plt.savefig(savingPath + 'sample.pdf', dpi=300)
    # plt.show()

    # return [DRR, DRRMask]

    return [croppedDRR, binaryDRRMask, centerOfMass]

## ------------------------------------------------------------------------------------