"""
This file contains an example on how to:
- read model + ROI data from a serialized file
- apply inter fraction changes to the model and ROIMask
- save the resulting model

!!! does not work with public data for now since there is no struct in the public data !!!
"""
import copy
import matplotlib.pyplot as plt
from scipy.ndimage import zoom
import math
import time
import concurrent
from itertools import repeat
import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)

from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Data.DynamicData.breathingSignals import SyntheticBreathingSignal
from Core.Processing.DeformableDataAugmentationToolBox.generateDynamicSequencesFromModel import generateDeformationListFromBreathingSignalsAndModel
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import *
from Core.Processing.ImageSimulation.DRRToolBox import forwardProjection
from Core.Processing.ImageProcessing.image2DManip import getBinaryMaskFromROIDRR, get2DMaskCenterOfMass
from Core.Processing.ImageProcessing.crop3D import *
from Core.Processing.DeformableDataAugmentationToolBox.interFractionChanges import shrinkOrgan, translateData, rotateData
from Core.Processing.ImageProcessing.syntheticDeformation import applyBaselineShift

if __name__ == '__main__':

    ## paths selection ------------------------------------
    basePath = 'D:/ImageData/lung/Patient_4/1/FDG1/'
    dataPath = basePath + 'dynModAndROIs_bodyCropped.p'
    savingPath = basePath

    # parameters selection ------------------------------------
    bodyContourToUse = 'Body'
    targetContourToUse = 'GTV T'
    lungContourToUse = 'R lung'
    contourToAddShift = targetContourToUse

    # interfraction changes parameters
    baselineShift = [0, 0, 0]
    translation = [0, 0, 0]
    rotation = [0, 0, 0]
    shrinkSize = [5, 5, 5]

    # data loading
    patient = loadDataStructure(dataPath)[0]
    dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct = patient.getPatientDataOfType("RTStruct")[0]

    print('Available ROIs')
    rtStruct.print_ROINames()

    gtvContour = rtStruct.getContourByName(targetContourToUse)
    GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)
    GTVCenterOfMass = gtvContour.getCenterOfMass(dynMod.midp.origin, dynMod.midp.gridSize, dynMod.midp.spacing)
    GTVCenterOfMassInVoxels = getVoxelIndexFromPosition(GTVCenterOfMass, dynMod.midp)

    lungContour = rtStruct.getContourByName(lungContourToUse)
    lungMask = lungContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)
    lungCenterOfMass = lungContour.getCenterOfMass(dynMod.midp.origin, dynMod.midp.gridSize, dynMod.midp.spacing)
    lungCenterOfMassInVoxels = getVoxelIndexFromPosition(lungCenterOfMass, dynMod.midp)

    # plt.figure()
    # plt.title('before translate and rotate')
    # plt.imshow(dynMod.midp.imageArray[:, lungCenterOfMassInVoxels[1], :])
    # plt.imshow(lungMask.imageArray[:, lungCenterOfMassInVoxels[1], :], alpha=0.5)
    # plt.show()
    #
    # plt.figure()
    # plt.title('before translate and rotate')
    # plt.imshow(dynMod.midp.imageArray[:, :, GTVCenterOfMassInVoxels[2]])
    # plt.imshow(GTVMask.imageArray[:, :, GTVCenterOfMassInVoxels[2]], alpha=0.5)
    # plt.show()

    dynModCopy = copy.deepcopy(dynMod)
    GTVMaskCopy = copy.deepcopy(GTVMask)

    if contourToAddShift == targetContourToUse:
        dynMod, GTVMask = applyBaselineShift(dynMod, GTVMask, baselineShift)
    else:
        print('Not implemented in this script --> must use the get contour by name function')

    translateData(dynMod, translationInMM=translation)
    translateData(GTVMask, translationInMM=translation)
    translateData(lungMask, translationInMM=translation)

    rotateData(dynMod, rotationInDeg=rotation)
    rotateData(GTVMask, rotationInDeg=rotation)
    rotateData(lungMask, rotationInDeg=rotation)

    # fig, ax = plt.subplots(1, 2)
    # y_slice = 100
    # vmin = -1000
    # vmax = 1000
    # ax[0].imshow(dynModCopy.midp.imageArray[:, y_slice, :], cmap='gray', origin='upper', vmin=vmin, vmax=vmax)
    # ax[1].imshow(dynMod.midp.imageArray[:, y_slice, :], cmap='gray', origin='upper', vmin=vmin, vmax=vmax)
    # plt.show()

    # # Plot X-Z field
    # fig, ax = plt.subplots(1, 2)
    # y_slice = 100
    # vmin = -1000
    # vmax = 1000
    #
    # subsamplingForPlot = 1
    #
    # compXCopy = dynModCopy.deformationList[0].velocity.imageArray[:, y_slice, :, 0]
    # compZCopy = dynModCopy.deformationList[0].velocity.imageArray[:, y_slice, :, 2]
    # ratio = [compXCopy.shape[0] / dynModCopy.midp.imageArray.shape[0], compXCopy.shape[1] / dynModCopy.midp.imageArray.shape[2]]
    # compZCopy[0, 0] = 1
    # resizedImgCopy = zoom(dynModCopy.midp.imageArray[:, y_slice, :], ratio)
    # ax[0].imshow(resizedImgCopy.T[::subsamplingForPlot, ::subsamplingForPlot], cmap='gray', origin='upper', vmin=vmin, vmax=vmax)
    # ax[0].quiver(compXCopy.T[::subsamplingForPlot, ::subsamplingForPlot], compZCopy.T[::subsamplingForPlot, ::subsamplingForPlot], alpha=0.2, color='red', angles='xy', scale_units='xy', scale=0.5)
    # ax[0].set_xlabel('x')
    # ax[0].set_ylabel('z')
    #
    # compX = dynMod.deformationList[0].velocity.imageArray[:, y_slice, :, 0]
    # compZ = dynMod.deformationList[0].velocity.imageArray[:, y_slice, :, 2]
    # ratio = [compX.shape[0] / dynMod.midp.imageArray.shape[0], compX.shape[1] / dynMod.midp.imageArray.shape[2]]
    # compZ[0, 0] = 1
    # resizedImg = zoom(dynMod.midp.imageArray[:, y_slice, :], ratio)
    # ax[1].imshow(resizedImg.T[::subsamplingForPlot, ::subsamplingForPlot], cmap='gray', origin='upper', vmin=vmin, vmax=vmax)
    # ax[1].quiver(compX.T[::subsamplingForPlot, ::subsamplingForPlot], compZ.T[::subsamplingForPlot, ::subsamplingForPlot], alpha=0.2, color='red', angles='xy', scale_units='xy', scale=0.5)
    # ax[1].set_xlabel('x')
    # ax[1].set_ylabel('z')
    #
    # plt.show()

    # plt.figure()
    # plt.title('after translate and rotate')
    # plt.imshow(dynMod.midp.imageArray[:, lungCenterOfMassInVoxels[1], :])
    # plt.imshow(lungMask.imageArray[:, lungCenterOfMassInVoxels[1], :], alpha=0.5)
    # plt.show()
    #
    # plt.figure()
    # plt.title('after translate and rotate')
    # plt.imshow(dynMod.midp.imageArray[:, :, GTVCenterOfMassInVoxels[2]])
    # plt.imshow(GTVMask.imageArray[:, :, GTVCenterOfMassInVoxels[2]], alpha=0.5)
    # plt.show()

    # plt.figure()
    # plt.title('after translate and rotate')
    # plt.imshow(dynMod.midp.imageArray[:, lungCenterOfMassInVoxels[1], :])
    # plt.imshow(lungMask.imageArray[:, lungCenterOfMassInVoxels[1], :], alpha=0.5)
    # plt.show()

    shrinkedDynMod, shrinkedOrganMask, newMask3DCOM = shrinkOrgan(dynMod, GTVMask, shrinkSize=shrinkSize)
    shrinkedDynMod.name = 'MidP_ShrinkedGTV'
    patient.appendPatientData(shrinkedDynMod)
    patient.appendPatientData(shrinkedOrganMask)

    fig, ax = plt.subplots(1, 3)
    plt.title('after baseline shift, translate, rotate and shrink')
    ax[0].imshow(dynModCopy.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[0].imshow(GTVMaskCopy.imageArray[:, GTVCenterOfMassInVoxels[1], :], alpha=0.5)
    ax[1].imshow(shrinkedDynMod.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[1].imshow(shrinkedOrganMask.imageArray[:, GTVCenterOfMassInVoxels[1], :], alpha=0.5)
    ax[2].imshow(dynModCopy.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :] - shrinkedDynMod.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    # plt.imshow(lungMask.imageArray[:, lungCenterOfMassInVoxels[1], :], alpha=0.5)
    plt.show()

    ## if you want to see the crop in the GUI you can save the data in cropped version
    # saveSerializedObjects(patient, savingPath + 'crop_InterFracChanged_ModelAndROIs')



