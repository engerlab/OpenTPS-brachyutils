import cupy
import cupyx.scipy.ndimage
import numpy as np
from opentps.core.data.dynamicData.dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData.dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images._vectorField3D import VectorField3D
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.processing.imageProcessing.cupyImageProcessing import rotateCupy, translateCupy
from opentps.core.processing.imageProcessing.sitkImageProcessing import rotateImage3DSitk

import copy
from skimage.morphology import rectangle
from scipy.spatial.transform import Rotation as R


# TODO: add the cupy check and eventually propose alternative librairies (sitk, scipy)

## ------------------------------------------------------------------------------------------------
def shrinkOrgan(model, organMask, shrinkSize = [2, 2, 2]):

    """

    Parameters
    ----------
    model
    organMask
    shrinkSize

    Returns
    -------

    """

    organCOM = organMask.centerOfMass
    if not np.array(shrinkSize == np.array([0, 0, 0])).all():
        print("Start shrinking the organ", organMask.name)
        ## get organ COM
        # organCOM = organMask.centerOfMass
        # organCOMInVoxels = getVoxelIndexFromPosition(organCOM, model.midp)
        # print('Used ROI name', organMask.name)
        # print('Used ROI center of mass :', organCOM)
        # print('Used ROI center of mass in voxels:', organCOMInVoxels)
        # plt.figure()
        # plt.imshow(model.midp.imageArray[:, :, organCOMInVoxels[2]])
        # plt.imshow(organMask.imageArray[:, :, organCOMInVoxels[2]], alpha=0.5)
        # plt.show()

        ## get the shrink size in voxels
        print('Shrink size in mm:', shrinkSize)
        for i in range(3):
            if shrinkSize[i] < 0:
                shrinkSize[i] = 0
                print("Negative Shrink size not allowed, the new vector in mm is: ", shrinkSize)
              
        shrinkSizeInVoxels = np.round(shrinkSize / model.midp.spacing).astype(np.uint8)
        print('Shrink size in voxels:', shrinkSizeInVoxels)

        if not np.array(shrinkSizeInVoxels == np.array([0, 0, 0])).all():

            # get the structural element used for the erosion and dilation
            structuralElementErosionYZ = rectangle((2 * shrinkSizeInVoxels[1]) + 1, ( 2 * shrinkSizeInVoxels[2]) + 1)
            structuralElementErosionXYZ = np.stack([structuralElementErosionYZ for _ in range((2 * shrinkSizeInVoxels[0]) + 1)])

            structuralElementDilationYZ = rectangle(3, 3)
            structuralElementDilationXYZ = np.stack([structuralElementDilationYZ for _ in range(3)])

            ## to visualize the used structural element
            # print('Structural element shape:', structuralElementErosionXYZ.shape)
            # fig = plt.figure(figsize=(8, 8))
            # ax = fig.add_subplot(1, 1, 1, projection=Axes3D.name)
            # ax.voxels(structuralElementErosionXYZ)
            # plt.show()

            ## apply an erosion and dilation using Cupy
            cupyOrganMask = cupy.asarray(organMask.imageArray)
            erodedOrganMask = cupy.asnumpy(cupyx.scipy.ndimage.binary_erosion(cupyOrganMask, structure=cupy.asarray(structuralElementErosionXYZ)))
            dilatedOrganMask = cupy.asnumpy(cupyx.scipy.ndimage.binary_dilation(cupyOrganMask, structure=cupy.asarray(structuralElementDilationXYZ)))

            ## get the new COM after mask erosion
            organROIMaskCopy = copy.deepcopy(organMask)
            organROIMaskCopy.imageArray = erodedOrganMask
            erodedMaskCOM = organROIMaskCopy.centerOfMass

            ## get the eroded and dilated band masks
            erodedBand = organMask.imageArray ^ erodedOrganMask
            dilatedBand = dilatedOrganMask ^ organMask.imageArray

            # ## to visualize the eroded and dilated band masks
            # plt.figure()
            # plt.subplot(1, 2, 1)
            # plt.imshow(erodedBand[:, organCOMInVoxels[1], :])
            # plt.subplot(1, 2, 2)
            # plt.imshow(dilatedBand[:, organCOMInVoxels[1], :])
            # plt.show()

            ## to get the bands coordinates
            erodedBandPoints = np.argwhere(erodedBand == 1)
            dilatedBandPoints = np.argwhere(dilatedBand == 1)

            newArray = copy.deepcopy(model.midp.imageArray)

            print('Start filling the eroded band with new values, this might take a few minutes')

            for pointIndex, point in enumerate(erodedBandPoints):

                ## get the distances between the current point of the eroded band with all the points in the dilated band
                distances = np.sqrt(np.sum(np.square(dilatedBandPoints - point), axis=1))
                distances = np.expand_dims(distances, axis=1)

                ## add the distances to the array of point coordinates
                dilBandPointsAndDists = np.concatenate((dilatedBandPoints, distances), axis=1)

                ## sort the points in function of the distance
                sortedPointAndDists = dilBandPointsAndDists[dilBandPointsAndDists[:, 3].argsort()]

                ## take closest 2% of points
                sortedPointAndDists = sortedPointAndDists[:int((2 / 100) * dilBandPointsAndDists.shape[0])]

                ## get the selected 2% of point coordinates in integer
                sortedPointAndDists = sortedPointAndDists[:, :3].astype(np.uint16)

                ## get the values in the original image at the selected coordinates
                indexlisttranspose = sortedPointAndDists.T.tolist()
                imageValuesToUse = model.midp.imageArray[tuple(indexlisttranspose)]


                ## get the mean value of those points, add a correction factor (not ideal)
                meanValueOfClosestPoints = np.mean(imageValuesToUse)
                meanValueOfClosestPoints -= 180 ## this is not ideal, hard coded value which might not work for other organs than lung

                ## get a random value around the mean value
                newValue = np.random.normal(meanValueOfClosestPoints, 70)

                ## replace the voxel of the eroded band with the nex value
                newArray[point[0], point[1], point[2]] = newValue

            ## smooth the result
            cupyNewImg = cupy.asarray(newArray)
            smoothedImg = cupy.asnumpy(cupyx.scipy.ndimage.gaussian_filter(cupyNewImg, 1))

            ## replace the target area with the smoothed img
            newImage = copy.deepcopy(model.midp.imageArray)
            newImage[dilatedOrganMask] = smoothedImg[dilatedOrganMask]

            newModel = copy.deepcopy(model)
            newModel.midp.imageArray = newImage
            newModel.midp.name = 'MidP_IFC'

            organMask.imageArray = erodedOrganMask

            # ## to visualize the steps
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

            return newModel, organMask, erodedMaskCOM

        else:
            return model, organMask, organCOM

    else:
        return model, organMask, organCOM

## ------------------------------------------------------------------------------------------------
def rotateData(data, rotationInDeg=[0, 0, 0]):

    """

    Parameters
    ----------
    data
    rotationInDeg

    Returns
    -------

    """

    rotationInDeg = np.array(rotationInDeg)
    if not np.array(rotationInDeg == np.array([0, 0, 0])).all():

        if isinstance(data, Dynamic3DModel):
            print('Rotate the Dynamic3DModel of', rotationInDeg, 'degrees')
            print('Rotate dynamic 3D model - midp image')
            rotateData(data.midp, rotationInDeg=rotationInDeg)
            
            for field in data.deformationList:
                if field.velocity != None:
                    print('Rotate dynamic 3D model - velocity field')
                    rotateData(field.velocity, rotationInDeg=rotationInDeg)
                if field.displacement != None:
                    print('Rotate dynamic 3D model - displacement field')
                    rotateData(field.displacement, rotationInDeg=rotationInDeg)

        if isinstance(data, Dynamic3DSequence):
            print('Rotate the Dynamic3DSequence of', rotationInDeg, 'degrees')
            for image3D in data.dyn3DImageList:
                rotateData(image3D, rotationInDeg=rotationInDeg)

        if isinstance(data, Image3D):

            if isinstance(data, VectorField3D):

                rotate3DVectorFields(data, rotationInDeg=rotationInDeg)
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
                print('Rotate ROIMask of', rotationInDeg, 'degrees')
                for i in range(3):
                    if rotationInDeg[i] != 0:
                        rotateImage3DSitk(data, rotAngleInDeg=rotationInDeg[i], rotAxis=i, cval=0)

            else:
                print('Rotate Image3D of', rotationInDeg, 'degrees')
                # data.imageArray = rotateCupy(data.imageArray, rotationInDeg=rotationInDeg)
                for i in range(3):
                    if rotationInDeg[i] != 0:
                        rotateImage3DSitk(data, rotAngleInDeg=rotationInDeg[i], rotAxis=i)

## --------------------------------------------------------------------------------------
def rotate3DVectorFields(vectorField, rotationInDeg=[0, 0, 0]):

    """

    Parameters
    ----------
    vectorField
    rotationInDeg

    Returns
    -------

    """

    print('Apply rotation to field imageArray', rotationInDeg)
    for i in range(3):
        if rotationInDeg[i] != 0:
            rotateImage3DSitk(vectorField, rotAngleInDeg=rotationInDeg[i], rotAxis=i, cval=0)

    print('Apply rotation to field vectors', rotationInDeg)

    r = R.from_rotvec(rotationInDeg, degrees=True)

    flattenedVectorField = vectorField.imageArray.reshape((vectorField.gridSize[0] * vectorField.gridSize[1] * vectorField.gridSize[2], 3))

    flattenedVectorField = r.apply(flattenedVectorField, inverse=True)

    vectorField.imageArray = flattenedVectorField.reshape((vectorField.gridSize[0], vectorField.gridSize[1], vectorField.gridSize[2], 3))


## --------------------------------------------------------------------------------------
def translateData(data, translationInMM=[0, 0, 0], cval=-1000):

    """

    Parameters
    ----------
    data
    translationInMM
    cval

    Returns
    -------

    """

    if not np.array(translationInMM == np.array([0, 0, 0])).all():

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
                print('Translate VectorField3D of', translationInMM, 'mm, --> translation In Pixels', translationInPixels, 'pixels')
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
                print('Translate ROIMask of', translationInMM, 'mm, --> translation In Pixels', translationInPixels, 'pixels')
                data.imageArray = data.imageArray.astype(np.float)
                data.imageArray = translateCupy(data.imageArray, translationInPixels=translationInPixels, cval=0)
                data.imageArray = data.imageArray > 0.5

            else:
                print('Translate Image3D of', translationInMM, 'mm, --> translation In Pixels', translationInPixels, 'pixels')
                data.imageArray = translateCupy(data.imageArray, translationInPixels=translationInPixels)





def translateAndRotate3DVectorFields(vectorField, translation=[0, 0, 0, 0], rotation=[0, 0, 0]):

    """

    Parameters
    ----------
    vectorField
    translation
    rotation

    Returns
    -------

    """

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

