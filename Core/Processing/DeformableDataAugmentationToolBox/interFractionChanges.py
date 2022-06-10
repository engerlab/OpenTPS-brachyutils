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
from Core.Processing.ImageProcessing.cupyImageProcessing import rotateCupy, translateCupy
from Core.Processing.ImageProcessing.sitkImageProcessing import rotateImage3DSitk


import copy
from skimage.morphology import cube, octahedron, ball, rectangle
from scipy.spatial.transform import Rotation as R
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
def rotateData(data, rotationInDeg=[0, 0, 0]):

    rotationInDeg = np.array(rotationInDeg)

    if isinstance(data, Dynamic3DModel):
        print('Rotate the Dynamic3DModel of', rotationInDeg, 'degrees')
        print('Rotate dynamic 3D model - midp image')
        rotateData(data.midp, rotationInDeg=rotationInDeg)

        for field in data.deformationList:
            if field.velocity != None:
                print('Translate and/or rotate dynamic 3D model - velocity field')
                rotateData(field.velocity, rotationInDeg=rotationInDeg)
            if field.displacement != None:
                print('Translate and/or rotate dynamic 3D model - displacement field')
                rotateData(field.displacement, rotationInDeg=rotationInDeg)

    if isinstance(data, Dynamic3DSequence):
        print('Rotate the Dynamic3DSequence of', rotationInDeg, 'degrees')
        for image3D in data.dyn3DImageList:
            rotateData(image3D, rotationInDeg=rotationInDeg)

    if isinstance(data, Image3D):

        if isinstance(data, VectorField3D):

            data.imageArray = rotate3DVectorFields(data.imageArray, rotation=rotationInDeg)
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

            rotateImage3DSitk(data)

            data.imageArray = data.imageArray.astype(np.float)
            data.imageArray = rotateCupy(data.imageArray, rotationInDeg=rotationInDeg, cval=0)
            data.imageArray = data.imageArray > 0.5

            # rotateSitk(field.velocity)

        else:
            print('Rotate the Image3D of', rotationInDeg, 'degrees')
            # data.imageArray = rotateCupy(data.imageArray, rotationInDeg=rotationInDeg)
            for i in range(3):
                if rotationInDeg[i] != 0: data = rotateImage3DSitk(data, rotAngleInDeg=rotationInDeg[i], rotAxis=i)


def translateData(data, translationInMM=[0, 0, 0], cval=-1000):

    translationInMM = np.array(translationInMM)

    if isinstance(data, Dynamic3DModel):
        print('Translate Dynamic3DModel of', translationInMM, 'mm')
        print('Translate dynamic 3D model - midp image')
        translateData(data.midp, translationInMM=translationInMM)

        for field in data.deformationList:
            if field.velocity != None:
                print('Translate dynamic 3D model - velocity field')
                translateData(field.velocity, translationInMM=translationInMM)
            if field.displacement != None:
                print('Translate dynamic 3D model - displacement field')
                translateData(field.displacement,  translationInMM=translationInMM)

    if isinstance(data, Dynamic3DSequence):
        print('Translate Dynamic3DSequence of', translationInMM, 'mm')
        for image3D in data.dyn3DImageList:
            translateData(image3D, translationInMM=translationInMM)

    if isinstance(data, Image3D):

        translationInPixels = translationInMM / data.spacing

        if isinstance(data, VectorField3D):

            translationInPixels = np.append(translationInPixels, [0])
            data.imageArray = translateCupy(data.imageArray, translationInPixels=translationInPixels, cval=0)
            # data.imageArray = translateAndRotate3DVectorFields(data.imageArray, translation=translationInPixels)
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
            data.imageArray = data.imageArray.astype(np.float)
            data.imageArray = translateCupy(data.imageArray, translationInPixels=translationInPixels, cval=0)
            data.imageArray = data.imageArray > 0.5

        else:
            print('Translate Image3D of', translationInMM, 'mm, --> translation In Pixels', translationInPixels, 'pixels')
            data.imageArray = translateCupy(data.imageArray, translationInPixels=translationInPixels)




def rotate3DVectorFields(vectorField, rotation=[0, 0, 0]):

    if not np.array(rotation == np.array([0, 0, 0])).all():
        print('in translateAndRotate3DVectorFields in if not')

        vectorField = rotateCupy(vectorField, rotationInDeg=rotation, cval=0)

    if not np.array(rotation == np.array([0, 0, 0])).all():
        print('Apply rotation to vectors', rotation)

        r = R.from_rotvec(rotation, degrees=True)

        flattenedVectorField = vectorField.reshape((vectorField.shape[0] * vectorField.shape[1] * vectorField.shape[2], 3))
        # voxel = 4000
        # print(flattenedVectorField.shape)
        # print(flattenedVectorField[voxel])

        flattenedVectorField = r.apply(flattenedVectorField, inverse=True)

        # print(flattenedVectorField.shape)
        # print(flattenedVectorField[voxel])

        vectorField = flattenedVectorField.reshape((vectorField.shape[0], vectorField.shape[1], vectorField.shape[2], 3))
        # print(vectorField.shape)

    print('!!! after vector rot', vectorField[15, 10, 10])
    # print('in translateAndRotate3DVectorFields after', vectorField[10, 10, 10])

    return vectorField


def translateAndRotate3DVectorFields(vectorField, translation=[0, 0, 0, 0], rotation=[0, 0, 0]):
    # print('in translateAndRotate3DVectorFields before', vectorField[10, 10, 10])


    if not (np.array(translation == np.array([0, 0, 0])).all() and np.array(rotation == np.array([0, 0, 0])).all()):
        print('in translateAndRotate3DVectorFields in if not')

        vectorField = translateCupy(vectorField, translationInPixels=translation, cval=0)
        vectorField = rotateCupy(vectorField, rotationInDeg=rotation, cval=0)


    if not np.array(rotation == np.array([0, 0, 0])).all():
        print('Apply rotation to vectors', rotation)


        r = R.from_rotvec(rotation, degrees=True)

        flattenedVectorField = vectorField.reshape((vectorField.shape[0] * vectorField.shape[1] * vectorField.shape[2], 3))
        # voxel = 4000
        # print(flattenedVectorField.shape)
        # print(flattenedVectorField[voxel])

        flattenedVectorField = r.apply(flattenedVectorField, inverse=True)

        # print(flattenedVectorField.shape)
        # print(flattenedVectorField[voxel])

        vectorField = flattenedVectorField.reshape((vectorField.shape[0], vectorField.shape[1], vectorField.shape[2], 3))
        # print(vectorField.shape)

    print('!!! after vector rot', vectorField[15, 10, 10])
    # print('in translateAndRotate3DVectorFields after', vectorField[10, 10, 10])

    return vectorField

