import cupy
import cupyx.scipy.ndimage
import numpy as np
import matplotlib.pyplot as plt
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import getVoxelIndexFromPosition
import copy
from skimage.morphology import cube, octahedron, ball, rectangle
from mpl_toolkits.mplot3d import Axes3D
from scipy.ndimage import gaussian_filter


def shrinkOrgan(image, organContour, shrinkSize = [2, 2, 2]):

    ## get organ COM
    gtvCenterOfMass = organContour.getCenterOfMass(image.origin, image.gridSize, image.spacing)
    gtvCenterOfMassInVoxels = getVoxelIndexFromPosition(gtvCenterOfMass, image)
    print('Used ROI name', organContour.name)
    print('Used ROI center of mass :', gtvCenterOfMass)
    print('Used ROI center of mass in voxels:', gtvCenterOfMassInVoxels)

    GTVMask = organContour.getBinaryMask(origin=image.origin, gridSize=image.gridSize, spacing=image.spacing)

    # plt.figure()
    # plt.imshow(image.imageArray[:, :, gtvCenterOfMassInVoxels[2]])
    # plt.imshow(GTVMask.imageArray[:, :, gtvCenterOfMassInVoxels[2]], alpha=0.5)
    # plt.show()

    ## get the shrink size in voxels
    print('Shrink size in mm:', shrinkSize)
    shrinkSizeInVoxels = np.round(shrinkSize / image.spacing).astype(np.uint8)
    print('Shrink size in voxels:', shrinkSizeInVoxels)

    # get the structural element used for the erosion and dilation
    structuralElementYZ = rectangle(shrinkSizeInVoxels[1], shrinkSizeInVoxels[2])
    structuralElementXYZ = np.stack([structuralElementYZ for _ in range(shrinkSizeInVoxels[0])])

    # print('Structural element shape:', structuralElementXYZ.shape)
    # fig = plt.figure(figsize=(8, 8))
    # ax = fig.add_subplot(1, 1, 1, projection=Axes3D.name)
    # ax.voxels(structuralElementXYZ)
    # plt.show()

    ## apply an erosion and dilation using Cupy
    cupyGTVMask = cupy.asarray(GTVMask.imageArray)
    erodedGTVMask = cupy.asnumpy(cupyx.scipy.ndimage.binary_erosion(cupyGTVMask, structure=cupy.asarray(structuralElementXYZ)))
    dilatedGTVMask = cupy.asnumpy(cupyx.scipy.ndimage.binary_dilation(cupyGTVMask, structure=cupy.asarray(structuralElementXYZ)))

    erodedBand = GTVMask.imageArray ^ erodedGTVMask
    dilatedBand = dilatedGTVMask ^ GTVMask.imageArray

    # plt.figure()
    # plt.subplot(1, 2, 1)
    # plt.imshow(erodedBand[:, :, gtvCenterOfMassInVoxels[2]])
    # plt.subplot(1, 2, 2)
    # plt.imshow(dilatedBand[:, :, gtvCenterOfMassInVoxels[2]])
    # plt.show()

    erodedBandPoints = np.argwhere(erodedBand == 1)
    dilatedBandPoints = np.argwhere(dilatedBand == 1)

    newImg = copy.deepcopy(image)

    for pointIndex, point in enumerate(erodedBandPoints):


        # print(dilatedBandPoints - point)
        distances = np.sqrt(np.sum(np.square(dilatedBandPoints - point), axis=1))
        distances = np.expand_dims(distances, axis=1)
        # print(distances.shape)
        dilBandPointsAndDists = np.concatenate((dilatedBandPoints, distances), axis=1)


        # print(dilBandPointsAndDists.shape)
        # print(dilBandPointsAndDists[:10])
        # sortedPointAndDists = np.sort(dilBandPointsAndDists, axis=)
        sortedPointAndDists = dilBandPointsAndDists[dilBandPointsAndDists[:, 3].argsort()]

        ## take closest 10% of points
        sortedPointAndDists = sortedPointAndDists[:int((10 / 100) * dilBandPointsAndDists.shape[0])]
        # print('-----------')
        # print(sortedPointAndDists[:5])
        # print(sortedPointAndDists.shape)

        imageValuesToUse = image.imageArray[sortedPointAndDists[:, :3].astype(np.uint8)]

        # print(imageValuesToUse)
        meanValueOfClosestPoints = np.mean(imageValuesToUse)
        varValueOfClosestPoints = np.std(imageValuesToUse)

        meanValueOfClosestPoints -= 280
        newValue = np.random.normal(meanValueOfClosestPoints, 70)
        newImg.imageArray[point[0], point[1], point[2]] = newValue

        print('Point', pointIndex, point, 'meanValueOfClosestPointsAdjusted:', meanValueOfClosestPoints, 'new value:', newValue)


    cupyNewImg = cupy.asarray(newImg.imageArray)
    smoothedImg = cupy.asnumpy(cupyx.scipy.ndimage.gaussian_filter(cupyNewImg, 1))

    # smoothedImg = gaussian_filter(newImg.imageArray[GTVMask.imageArray], 0.5)
    newImg.imageArray[dilatedGTVMask] = smoothedImg[dilatedGTVMask]


    # erodedBandMean = np.mean(image.imageArray[erodedBand == 1])
    # dilatedBandMean = np.mean(image.imageArray[dilatedBand == 1])
    # print(erodedBandMean, dilatedBandMean)

    plt.figure()
    plt.subplot(2, 2, 1)
    # plt.imshow(image.imageArray[100:200, 100:200, gtvCenterOfMassInVoxels[2]])
    plt.imshow(smoothedImg[100:200, 100:200, gtvCenterOfMassInVoxels[2]])
    plt.subplot(2, 2, 2)
    plt.imshow(smoothedImg2[100:200, 100:200, gtvCenterOfMassInVoxels[2]])
    plt.subplot(2, 2, 3)
    plt.imshow(newImg.imageArray[100:200, 100:200, gtvCenterOfMassInVoxels[2]])
    plt.subplot(2, 2, 4)
    plt.imshow(newImg2.imageArray[100:200, 100:200, gtvCenterOfMassInVoxels[2]])
    # plt.imshow(image.imageArray[100:200, 100:200, gtvCenterOfMassInVoxels[2]]-newImg.imageArray[100:200, 100:200, gtvCenterOfMassInVoxels[2]])
    plt.show()

    fig, axs = plt.subplots(2, 1, constrained_layout=True)
    fig.suptitle('organ shrinking example', fontsize=16)
    axs[0].imshow(image.imageArray[:, :, gtvCenterOfMassInVoxels[2]])
    axs[0].set_title('original image')

    axs[1].imshow(image.imageArray[:, :, gtvCenterOfMassInVoxels[2]])
    axs[1].set_title('original image')

    plt.show()

    return newImg

def affineTransformCupy():

    cupyx.scipy.ndimage.shift()
    cupyx.scipy.ndimage.rotate()