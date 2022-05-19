import cupy
import cupyx.scipy.ndimage
import numpy as np
import matplotlib.pyplot as plt
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import getVoxelIndexFromPosition


def shrinkOrgan(image, organContour, shrinkSize = 2):

    print('in shrink organ')

    # print(image2)


    gtvCenterOfMass = organContour.getCenterOfMass(image.origin, image.gridSize, image.spacing)
    gtvCenterOfMassInVoxels = getVoxelIndexFromPosition(gtvCenterOfMass, image)
    print('Used ROI name', organContour.name)
    print('Used ROI center of mass :', gtvCenterOfMass)
    print('Used ROI center of mass in voxels:', gtvCenterOfMassInVoxels)

    GTVMask = organContour.getBinaryMask(origin=image.origin, gridSize=image.gridSize,
                                       spacing=image.spacing)

    plt.figure()
    plt.imshow(image.imageArray[:, :, gtvCenterOfMassInVoxels[2]])
    plt.imshow(GTVMask.imageArray[:, :, gtvCenterOfMassInVoxels[2]], alpha=0.5)
    plt.show()

    # cupyx.scipy.ndimage.binary_dilation()
    # cupyx.scipy.ndimage.binary_erosion()

    print(GTVMask.spacing)

    cupyGTVMask = cupy.asarray(GTVMask.imageArray)

    erodedGTVMask = cupy.asnumpy(cupyx.scipy.ndimage.binary_erosion(cupyGTVMask))
    dilatedGTVMask = cupy.asnumpy(cupyx.scipy.ndimage.binary_dilation(cupyGTVMask))

    erodedBand = GTVMask.imageArray ^ erodedGTVMask
    dilatedBand = dilatedGTVMask ^ GTVMask.imageArray

    plt.figure()
    plt.subplot(1, 2, 1)
    plt.imshow(erodedBand[:, :, gtvCenterOfMassInVoxels[2]])
    plt.subplot(1, 2, 2)
    plt.imshow(dilatedBand[:, :, gtvCenterOfMassInVoxels[2]])
    plt.show()

    print(np.argwhere(erodedBand == 1))

    erodedBandPoints = np.argwhere(erodedBand == 1)
    dilatedBandPoints = np.argwhere(dilatedBand == 1)

    print(type(dilatedBandPoints))
    print(dilatedBandPoints.shape)

    print('iciiiiii')
    print(erodedBandPoints[:5])
    print('----------')
    print((dilatedBandPoints-erodedBandPoints[0])[:5])
    print('----------')
    print(np.square((dilatedBandPoints-erodedBandPoints[0])[:5]))
    print('----------')
    print(np.sum(np.square((dilatedBandPoints-erodedBandPoints[0])[:5]), axis=1))
    print('----------')
    print(np.sqrt(np.sum(np.square((dilatedBandPoints-erodedBandPoints[0])[:5]), axis=1)))
    print(type(np.sqrt(np.sum(np.square((dilatedBandPoints - erodedBandPoints[0])[:5]), axis=1))))

    # thing = np.sqrt(np.sum(np.square((dilatedBandPoints - erodedBandPoints[0])[:5]), axis=1))
    #
    # dilBandPointsAndDists = np.concatenate(dilatedBandPoints, thing)

    for point in erodedBandPoints:
        distances = np.sqrt(np.sum(np.square(dilatedBandPoints - point[0]), axis=1))
        print(distances.shape)
        dilBandPointsAndDists = np.concatenate(dilatedBandPoints, distances)
        print(dilBandPointsAndDists.shape)
        distanceArray = erodedBandPoints - point
        # sum_sq = np.sum(np.square(point1 - point2))
        print(point)

    erodedBandMean = np.mean(image.imageArray[erodedBand == 1])
    dilatedBandMean = np.mean(image.imageArray[dilatedBand == 1])
    print(erodedBandMean, dilatedBandMean)
    

    return 0

def affineTransformCupy():

    cupyx.scipy.ndimage.shift()
    cupyx.scipy.ndimage.rotate()