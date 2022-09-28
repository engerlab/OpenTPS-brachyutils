"""
This file contains an example on how to:
- read model + ROI data from a serialized file
- apply inter-fraction changes to the model and ROIMask
- save the resulting model

!!! does not work with public data for now since there is no struct in the public data !!!
"""
import copy
import matplotlib.pyplot as plt
import time
import os
import sys

currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)

from opentps_core.opentps.core.IO import loadDataStructure
from opentps_core.opentps.core.Processing.DeformableDataAugmentationToolBox import shrinkOrgan, translateData, rotateData
from opentps_core.opentps.core import applyBaselineShift
from opentps_core.opentps.core import crop3DDataAroundBox

if __name__ == '__main__':

    ## paths selection ------------------------------------
    basePath = 'D:/ImageData/lung/Patient_12/1/FDG1/'
    dataPath = basePath + 'dynModAndROIs_bodyCropped.p'
    savingPath = basePath

    # organ = 'lung'
    # patientFolder = 'Patient_4'
    # patientComplement = '/1/FDG1'
    # basePath = '/DATA2/public/'
    #
    # resultFolder = '/test10/'
    # resultDataFolder = 'data/'
    #
    # dataPath = basePath + organ + '/' + patientFolder + patientComplement + '/dynModAndROIs_bodyCropped.p'
    # savingPath = basePath + organ + '/' + patientFolder + patientComplement + resultFolder



    # parameters selection ------------------------------------
    bodyContourToUse = 'patient'
    targetContourToUse = 'gtv t'
    lungContourToUse = 'r lung'

    # bodyContourToUse = 'Body'
    # targetContourToUse = 'GTV T'
    # lungContourToUse = 'R lung'

    contourToAddShift = targetContourToUse

    croppingContoursUsedXYZ = [targetContourToUse, bodyContourToUse, targetContourToUse]
    marginInMM = [50, 0, 100]

    # interfraction changes parameters
    baselineShift = [-5, 0, 30]
    translation = [0, 0, 0]
    rotation = [0, 0, 0]
    shrinkSize = [0, 0, 0]

    # GPU used
    usedGPU = 0

    try:
        import cupy
        cupy.cuda.Device(usedGPU).use()
    except:
        print('Module Cupy not found or selected GPU not available')

    # data loading
    patient = loadDataStructure(dataPath)[0]
    dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct = patient.getPatientDataOfType("RTStruct")[0]

    print('Available ROIs')
    rtStruct.print_ROINames()

    gtvContour = rtStruct.getContourByName(targetContourToUse)
    GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)
    gtvBox = getBoxAroundROI(GTVMask)
    GTVCenterOfMass = gtvContour.getCenterOfMass(dynMod.midp.origin, dynMod.midp.gridSize, dynMod.midp.spacing)
    GTVCenterOfMassInVoxels = getVoxelIndexFromPosition(GTVCenterOfMass, dynMod.midp)

    ## get the body contour to adjust the crop in the direction of the DRR projection
    bodyContour = rtStruct.getContourByName(bodyContourToUse)
    bodyMask = bodyContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)
    bodyBox = getBoxAroundROI(bodyMask)
    print('Body Box from contour', bodyBox)

    ##Define the cropping box
    croppingBox = [[], [], []]
    for i in range(3):
        if croppingContoursUsedXYZ[i] == bodyContourToUse:
            croppingBox[i] = bodyBox[i]
        elif croppingContoursUsedXYZ[i] == targetContourToUse:
            croppingBox[i] = gtvBox[i]

    ## crop the model data using the box
    crop3DDataAroundBox(dynMod, croppingBox, marginInMM=marginInMM)
    GTVCenterOfMass = gtvContour.getCenterOfMass(dynMod.midp.origin, dynMod.midp.gridSize, dynMod.midp.spacing)
    GTVCenterOfMassInVoxels = getVoxelIndexFromPosition(GTVCenterOfMass, dynMod.midp)

    ## get the mask in cropped version (the dynMod.midp is now cropped so its origin and gridSize has changed)
    GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize,
                                       spacing=dynMod.midp.spacing)

    # fig, ax = plt.subplots(1, 3)
    # fig.suptitle('Example of baseline shift, translate, rotate and shrink')
    # ax[0].imshow(dynMod.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    # ax[0].imshow(GTVMask.imageArray[:, GTVCenterOfMassInVoxels[1], :], alpha=0.5)
    # ax[1].imshow(dynMod.midp.imageArray[GTVCenterOfMassInVoxels[0], :, :])
    # ax[1].imshow(GTVMask.imageArray[GTVCenterOfMassInVoxels[0], :, :], alpha=0.5)
    # ax[2].imshow(dynMod.midp.imageArray[:, :, GTVCenterOfMassInVoxels[2]])
    # ax[2].imshow(GTVMask.imageArray[:, :, GTVCenterOfMassInVoxels[2]], alpha=0.5)
    # plt.show()

    dynModCopy = copy.deepcopy(dynMod)
    GTVMaskCopy = copy.deepcopy(GTVMask)

    startTime = time.time()

    print('-' * 50)
    if contourToAddShift == targetContourToUse:
        print('Apply baseline shift of', baselineShift, 'to', contourToAddShift)
        dynMod, GTVMask = applyBaselineShift(dynMod, GTVMask, baselineShift)
    else:
        print('Not implemented in this script --> must use the get contour by name function')

    print('-' * 50)
    translateData(dynMod, translationInMM=translation)
    translateData(GTVMask, translationInMM=translation)

    print('-'*50)
    rotateData(dynMod, rotationInDeg=rotation)
    rotateData(GTVMask, rotationInDeg=rotation)

    print('-' * 50)
    shrinkedDynMod, shrinkedOrganMask, newMask3DCOM = shrinkOrgan(dynMod, GTVMask, shrinkSize=shrinkSize)
    shrinkedDynMod.name = 'MidP_ShrinkedGTV'

    print('-' * 50)

    stopTime = time.time()
    print('time:', stopTime-startTime)

    patient.appendPatientData(shrinkedDynMod)
    patient.appendPatientData(shrinkedOrganMask)

    fig, ax = plt.subplots(1, 4)
    fig.suptitle('Example of baseline shift, translate, rotate and shrink')
    ax[0].imshow(dynModCopy.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    # ax[0].imshow(GTVMaskCopy.imageArray[:, GTVCenterOfMassInVoxels[1], :], alpha=0.5)
    ax[0].set_title('Initial image and target mask')
    ax[1].imshow(shrinkedDynMod.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    # ax[1].imshow(shrinkedOrganMask.imageArray[:, GTVCenterOfMassInVoxels[1], :], alpha=0.5)
    ax[1].set_title('after inter fraction changes')
    ax[2].imshow(dynModCopy.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :] - shrinkedDynMod.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[2].set_title('image difference')
    ax[3].imshow(GTVMaskCopy.imageArray[:, GTVCenterOfMassInVoxels[1], :] ^ shrinkedOrganMask.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[3].set_title('mask difference')
    plt.show()
