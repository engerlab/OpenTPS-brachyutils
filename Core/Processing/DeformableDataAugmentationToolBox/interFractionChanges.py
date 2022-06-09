import cupy
import cupyx.scipy.ndimage
import numpy as np
import matplotlib.pyplot as plt
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import getVoxelIndexFromPosition
from Core.Data.DynamicData.dynamic3DModel import Dynamic3DModel
from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.vectorField3D import VectorField3D
from Core.Data.Images.roiMask import ROIMask
import copy
from skimage.morphology import cube, octahedron, ball, rectangle
from mpl_toolkits.mplot3d import Axes3D
from scipy.ndimage import gaussian_filter

# TODO: add the cupy check and eventually propose alternative librairies (sitk, scipy)

## ------------------------------------------------------------------------------------------------
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


## ------------------------------------------------------------------------------------------------
def translateAndRotateData(data, translationInMM=[0, 0, 0], rotationInDeg=[0, 0, 0]):

    if isinstance(data, Dynamic3DModel):
        print('Translate and/or rotate the Dynamic3DModel of', translationInMM, 'mm and', rotationInDeg, 'degrees')
        print('Translate and/or rotate dynamic 3D model - midp image')
        translateAndRotateData(data.midp, translationInMM=translationInMM, rotationInDeg=rotationInDeg)

        for field in data.deformationList:
            if field.velocity != None:
                print('Translate and/or rotate dynamic 3D model - velocity field')
                translateAndRotateData(field.velocity,  translationInMM=translationInMM, rotationInDeg=rotationInDeg)
            if field.displacement != None:
                print('Translate and/or rotate dynamic 3D model - displacement field')
                translateAndRotateData(field.displacement,  translationInMM=translationInMM, rotationInDeg=rotationInDeg)

    if isinstance(data, Dynamic3DSequence):
        print('Translate and/or rotate the Dynamic3DSequence of', translationInMM, 'mm and', rotationInDeg, 'degrees')
        for image3D in data.dyn3DImageList:
            translateAndRotateData(image3D, translationInMM=translationInMM, rotationInDeg=rotationInDeg)

    if isinstance(data, Image3D):

        translationInPixels = translationInMM / data.spacing

        if isinstance(data, VectorField3D):
            translationInPixels = np.append(translationInPixels, [0])

            data.imageArray = translateAndRotate3DVectorFields(data.imageArray, translation=translationInPixels, rotation=rotationInDeg, cval=0)
            # # Plot X-Z field
            # fig, ax = plt.subplots(3, 3)
            # y_slice = 100
            # compX = data.imageArray[:, y_slice, :, 0]
            # compZ = data.imageArray[:, y_slice, :, 2]
            # compZ[0, 0] = 1
            # ax[1, 0].imshow(reg.deformed.imageArray[:, y_slice, :].T[::1, ::1], cmap='gray', origin='upper', vmin=vmin, vmax=vmax)
            # ax[1, 0].quiver(compX.T[::1, ::1], compZ.T[::1, ::1], alpha=0.2, color='red', angles='xy', scale_units='xy', scale=1)
            # ax[1, 0].set_xlabel('x')
            # ax[1, 0].set_ylabel('z')
            # ax[1, 1].imshow(diff_before.imageArray[:, y_slice, :].T[::1, ::1], cmap='gray', origin='upper', vmin=2 * vmin, vmax=2 * vmax)
            # ax[1, 1].set_xlabel('x')
            # ax[1, 1].set_ylabel('z')
            # ax[1, 2].imshow(diff_after.imageArray[:, y_slice, :].T[::1, ::1], cmap='gray', origin='upper', vmin=2 * vmin, vmax=2 * vmax)
            # ax[1, 2].set_xlabel('x')
            # ax[1, 2].set_ylabel('z')

        elif isinstance(data, ROIMask):
            # print(type(data.imageArray[0, 0, 0]))
            # plt.figure()
            # plt.imshow(data.imageArray[:, :, 109])
            # plt.show()
            data.imageArray = data.imageArray.astype(np.float)
            data.imageArray = translateAndRotateCupy(data.imageArray, translation=translationInPixels, rotation=rotationInDeg, cval=0)
            data.imageArray = data.imageArray > 0.5
            # plt.figure()
            # plt.imshow(data.imageArray[:, :, 109])
            # plt.show()
        else:
            print('Translate and/or rotate the Image3D of', translationInMM, 'mm and', rotationInDeg, 'degrees. --> ', 'translation In Pixels', translationInPixels, 'pixels')
            data.imageArray = translateAndRotateCupy(data.imageArray, translation=translationInPixels, rotation=rotationInDeg)



## ------------------------------------------------------------------------------------------------
def translateAndRotateCupy(dataArray, translation=[0, 0, 0], rotation=[0, 0, 0], cval=-1000):

    cupyData = cupy.asarray(dataArray)

    if list(translation) != [0, 0, 0] or list(translation) != [0, 0, 0, 0]:
        cupyData = cupyx.scipy.ndimage.shift(cupyData, translation, mode='constant', cval=cval)

    if rotation != [0, 0, 0]:
        if rotation[0] != 0:
            cupyData = cupyx.scipy.ndimage.rotate(cupyData, rotation[0], axes=[1, 2], reshape=False, mode='constant', cval=cval)
        if rotation[1] != 0:
            cupyData = cupyx.scipy.ndimage.rotate(cupyData, rotation[1], axes=[0, 2], reshape=False, mode='constant', cval=cval)
        if rotation[2] != 0:
            cupyData = cupyx.scipy.ndimage.rotate(cupyData, rotation[2], axes=[0, 1], reshape=False, mode='constant', cval=cval)

    return cupy.asnumpy(cupyData)

def translateAndRotate3DVectorFields(vectorField, translation=[0, 0, 0], rotation=[0, 0, 0], cval=-1000):
    print('in translateAndRotate3DVectorFields')
    print(vectorField.shape)
    from scipy.spatial.transform import Rotation as R

    flattenedVectorField = vectorField.reshape((vectorField.shape[0] * vectorField.shape[1] * vectorField.shape[2], 3))

    if rotation != [0, 0, 0]:
        r = R.from_rotvec(rotation, degrees=True)

    voxel = 4000
    print(flattenedVectorField.shape)
    print(flattenedVectorField[voxel])

    flattenedVectorField = r.apply(flattenedVectorField, inverse=True)

    print(flattenedVectorField.shape)
    print(flattenedVectorField[voxel])

    vectorField = flattenedVectorField.reshape((vectorField.shape[0], vectorField.shape[1], vectorField.shape[2], 3))
    print(vectorField.shape)

    translateAndRotateCupy(vectorField, translation=translation, rotation=rotation)

    return vectorField

