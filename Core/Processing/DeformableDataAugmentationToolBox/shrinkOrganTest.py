import cupy
import cupyx.scipy.ndimage
import numpy as np
import matplotlib.pyplot as plt
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import getVoxelIndexFromPosition
import copy
from skimage.morphology import cube, octahedron, ball, rectangle
from mpl_toolkits.mplot3d import Axes3D
from scipy.ndimage import gaussian_filter


def shrinkOrgan(model, organMask, shrinkSize = [2, 2, 2]):

    ## get organ COM
    organCOM = organMask.centerOfMass
    organCOMInVoxels = getVoxelIndexFromPosition(organCOM, model.midp)
    # print('Used ROI name', organMask.name)
    # print('Used ROI center of mass :', organCOM)
    # print('Used ROI center of mass in voxels:', organCOMInVoxels)
    # plt.figure()
    # plt.imshow(model.midp.imageArray[:, :, organCOMInVoxels[2]])
    # plt.imshow(organMask.imageArray[:, :, organCOMInVoxels[2]], alpha=0.5)
    # plt.show()

    ## get the shrink size in voxels
    print('Shrink size in mm:', shrinkSize)
    shrinkSizeInVoxels = np.round(shrinkSize / model.midp.spacing).astype(np.uint8)
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
    cupyOrganMask = cupy.asarray(organMask.imageArray)
    erodedOrganMask = cupy.asnumpy(cupyx.scipy.ndimage.binary_erosion(cupyOrganMask, structure=cupy.asarray(structuralElementXYZ)))
    dilatedOrganMask = cupy.asnumpy(cupyx.scipy.ndimage.binary_dilation(cupyOrganMask, structure=cupy.asarray(structuralElementXYZ)))

    ## get the new COM after mask erosion
    organROIMaskCopy = copy.deepcopy(organMask)
    organROIMaskCopy.imageArray = erodedOrganMask
    erodedMaskCOM = organROIMaskCopy.centerOfMass

    erodedBand = organMask.imageArray ^ erodedOrganMask
    dilatedBand = dilatedOrganMask ^ organMask.imageArray

    # plt.figure()
    # plt.subplot(1, 2, 1)
    # plt.imshow(erodedBand[:, :, organCOMInVoxels[2]])
    # plt.subplot(1, 2, 2)
    # plt.imshow(dilatedBand[:, :, organCOMInVoxels[2]])
    # plt.show()

    erodedBandPoints = np.argwhere(erodedBand == 1)
    dilatedBandPoints = np.argwhere(dilatedBand == 1)

    newArray = copy.deepcopy(model.midp.imageArray)

    print('Start filling the eroded band with new values, this might take a few minutes')

    for pointIndex, point in enumerate(erodedBandPoints):

        distances = np.sqrt(np.sum(np.square(dilatedBandPoints - point), axis=1))
        distances = np.expand_dims(distances, axis=1)

        ##
        dilBandPointsAndDists = np.concatenate((dilatedBandPoints, distances), axis=1)

        ##
        sortedPointAndDists = dilBandPointsAndDists[dilBandPointsAndDists[:, 3].argsort()]

        ## take closest 10% of points
        sortedPointAndDists = sortedPointAndDists[:int((10 / 100) * dilBandPointsAndDists.shape[0])]


        imageValuesToUse = model.midp.imageArray[sortedPointAndDists[:, :3].astype(np.uint8)]

        meanValueOfClosestPoints = np.mean(imageValuesToUse)
        # varValueOfClosestPoints = np.std(imageValuesToUse)

        ## this is not ideal, hard coded value which might not work for other organs than lung
        meanValueOfClosestPoints -= 280

        newValue = np.random.normal(meanValueOfClosestPoints, 70)
        newArray[point[0], point[1], point[2]] = newValue

        # print('Point', pointIndex, point, 'meanValueOfClosestPointsAdjusted:', meanValueOfClosestPoints, 'new value:', newValue)


    cupyNewImg = cupy.asarray(newArray)
    smoothedImg = cupy.asnumpy(cupyx.scipy.ndimage.gaussian_filter(cupyNewImg, 1))

    newModel = copy.deepcopy(model)
    newModel.midp.imageArray[dilatedOrganMask] = smoothedImg[dilatedOrganMask]
    newModel.midp.name = 'MidP_ShrinkedGTV'

    # erodedBandMean = np.mean(image.imageArray[erodedBand == 1])
    # dilatedBandMean = np.mean(image.imageArray[dilatedBand == 1])
    # print(erodedBandMean, dilatedBandMean)

    # fig, axs = plt.subplots(1, 5, constrained_layout=True)
    # fig.suptitle('organ shrinking example', fontsize=16)
    # axs[0].imshow(model.midp.imageArray[:, :, organCOMInVoxels[2]])
    # axs[0].set_title('original image')
    #
    # axs[1].imshow(newArray[:, :, organCOMInVoxels[2]])
    # axs[1].set_title('values replaced image')
    #
    # axs[2].imshow(smoothedImg[:, :, organCOMInVoxels[2]])
    # axs[2].set_title('smoothed image')
    #
    # axs[3].imshow(newModel.midp.imageArray[:, :, organCOMInVoxels[2]])
    # axs[3].set_title('result image')
    #
    # axs[4].imshow(model.midp.imageArray[:, :, organCOMInVoxels[2]] - newModel.midp.imageArray[:, :, organCOMInVoxels[2]])
    # axs[4].set_title('original-shrinked diff')
    #
    # plt.show()

    return newModel, erodedOrganMask, erodedMaskCOM

def affineTransformCupy():

    cupyx.scipy.ndimage.shift()
    cupyx.scipy.ndimage.rotate()