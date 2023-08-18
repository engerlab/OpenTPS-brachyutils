import copy
import numpy as np
import logging
logger = logging.getLogger(__name__)

from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data._roiContour import ROIContour
from opentps.core.data.images._deformation3D import Deformation3D
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
import opentps.core.processing.imageProcessing.filter3D as imageFilter3D
from opentps.core.processing.imageProcessing import resampler3D
from opentps.core.processing.imageProcessing.imageTransform3D import getVoxelIndexFromPosition
from opentps.core.processing.segmentation.segmentationCT import compute3DStructuralElement
from opentps.core.processing.imageProcessing.roiMasksProcessing import buildStructElem
from opentps.core.processing.imageProcessing.filter3D import gaussConv


def applyBaselineShift(inputData, ROI, shift, sigma=2, tryGPU=True):
    """
    apply a baseline shift to the image and the ROI

    Parameters
    ----------
    inputData : Dynamic3DModel or Image3D
        the image to deform
    ROI : ROIContour or ROIMask
        the ROI to deform
    shift : np.array
        the shift to apply in mm
    sigma : float
        the sigma of the gaussian used to smooth the deformation
    tryGPU : bool
        if True, try to use the GPU

    Returns
    -------
    Dynamic3DModel or Image3D
        the deformed image
    ROIContour or ROIMask
        the deformed ROI
    """
    
    if not np.array(shift == np.array([0, 0, 0])).all(): ## check if there is a shift to apply

        if isinstance(inputData, Dynamic3DModel):
            model = inputData.copy()
            image = inputData.midp
        else:
            image = inputData

        if isinstance(ROI, ROIContour):
            mask = ROI.getBinaryMask(origin=image.origin, gridSize=image.gridSize, spacing=image.spacing)
        elif isinstance(ROI, ROIMask):
            mask = ROI

        maskMoving = mask.copy()
        maskMoving.dilateMask(struct=compute3DStructuralElement([sigma, sigma, sigma], spacing=maskMoving.spacing), tryGPU=tryGPU)

        maskFixed = maskMoving.copy()
        for i in range(3):
            maskFixed.origin[i] += shift[i]
        
        resampler3D.resampleImage3DOnImage3D(maskFixed, image, inPlace=True, fillValue=0)
        maskFixed._imageArray = np.logical_or(maskFixed.imageArray, maskMoving.imageArray)

        deformation = Deformation3D()
        deformation.initFromImage(image)

        cert = maskFixed.copy()
        cert._imageArray = maskFixed.imageArray.astype(np.float32)/1.1 + 0.1
        cert._imageArray[image.imageArray > 200] = 100

        for i in range(3):
            deformation = forceShiftInMask(deformation, maskFixed, shift)
            deformation.setVelocityArrayXYZ(
                imageFilter3D.normGaussConv(deformation.velocity.imageArray[:, :, :, 0], cert.imageArray, sigma, tryGPU=tryGPU),
                imageFilter3D.normGaussConv(deformation.velocity.imageArray[:, :, :, 1], cert.imageArray, sigma, tryGPU=tryGPU),
                imageFilter3D.normGaussConv(deformation.velocity.imageArray[:, :, :, 2], cert.imageArray, sigma, tryGPU=tryGPU))

        if isinstance(inputData, Dynamic3DModel):
            for i in range(len(model.deformationList)):
                model.deformationList[i].setVelocity(deformation.deformImage(inputData.deformationList[i].velocity, fillValue='closest', tryGPU=tryGPU))
            model.midp = deformation.deformImage(image, fillValue='closest', tryGPU=tryGPU)
            return model, deformation.deformImage(mask, fillValue='closest', tryGPU=tryGPU)
        else:
            return deformation.deformImage(image, fillValue='closest', tryGPU=tryGPU), deformation.deformImage(mask, fillValue='closest', tryGPU=tryGPU)
    else:
        if isinstance(inputData, Dynamic3DModel):
            return inputData, ROI
        else:
            return ROI


def forceShiftInMask(deformation,mask,shift):
    """
    force the deformation to be 0 in the mask

    Parameters
    ----------
    deformation : Deformation3D
        the deformation to modify
    mask : ROIMask
        the mask to use
    shift : np.array
        the shift to apply (same as the one applied to the image)

    Returns
    -------
    Deformation3D
        the modified deformation
    """

    for i in range(3):
        temp = deformation.velocity.imageArray[:, :, :, i]
        temp[mask.imageArray.nonzero()] = -shift[i]
        deformation.velocity._imageArray[:, :, :, i] = temp

    return deformation


def shrinkOrgan(model, organMask, shrinkSize = [2, 2, 2], tryGPU=True):

    """
    shrink the organ mask by a given size

    Parameters
    ----------
    model : Dynamic3DModel
        the model to modify
    organMask : ROIMask
        the organ mask to shrink
    shrinkSize : list
        the size of the shrink in mm in each direction (x, y, z)
    tryGPU : bool
        if True, try to use the GPU

    Returns
    -------
    Dynamic3DModel
        the modified model
    ROIMask
        the modified organ mask
    """

    organCOM = organMask.centerOfMass
    if not np.array(shrinkSize == np.array([0, 0, 0])).all():
        print("Start shrinking the organ", organMask.name)
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
        for i in range(3):
            if shrinkSize[i] < 0:
                shrinkSize[i] = 0
                print("Negative Shrink size not allowed, the new vector in mm is: ", shrinkSize)

        shrinkSizeInVoxels = np.round(shrinkSize / model.midp.spacing).astype(np.uint8)
        print('Shrink size in voxels:', shrinkSizeInVoxels)

        if not np.array(shrinkSizeInVoxels == np.array([0, 0, 0])).all():

            # get the structural elements used for the erosion and dilation
            structuralElementErosionXYZ = buildStructElem(shrinkSizeInVoxels)
            structuralElementDilationXYZ = buildStructElem(1.0)

            ## apply an erosion and dilation
            erodedOrganMask = organMask.copy()
            dilatedOrganMask = organMask.copy()
            erodedOrganMask.erodeMask(struct=structuralElementErosionXYZ, tryGPU=tryGPU)
            dilatedOrganMask.dilateMask(struct=structuralElementDilationXYZ, tryGPU=tryGPU)
            erodedOrganMask = erodedOrganMask.imageArray
            dilatedOrganMask = dilatedOrganMask.imageArray

            ## get the new COM after mask erosion
            # organROIMaskCopy = copy.deepcopy(organMask)
            # organROIMaskCopy.imageArray = erodedOrganMask
            # erodedMaskCOM = organROIMaskCopy.centerOfMass

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
            smoothedImg = gaussConv(newArray, sigma=1, tryGPU=tryGPU)

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

            return newModel, organMask

        else:
            return model, organMask

    else:
        return model, organMask
