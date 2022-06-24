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

from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import *
from Core.Processing.DeformableDataAugmentationToolBox.interFractionChanges import shrinkOrgan, translateData, rotateData
from Core.Processing.ImageProcessing.syntheticDeformation import applyBaselineShift

if __name__ == '__main__':

    organ = 'lung'
    patientFolder = 'Patient_1'
    patientComplement = '/1/FDG1'
    basePath = '/DATA2/public/'

    resultFolder = '/test10/'
    resultDataFolder = 'data/'

    dataPath = basePath + organ  + '/' + patientFolder + patientComplement + '/dynModAndROIs.p'
    savingPath = basePath + organ  + '/' + patientFolder + patientComplement + resultFolder

    # parameters selection ------------------------------------
    bodyContourToUse = 'Body'
    targetContourToUse = 'GTV T'
    lungContourToUse = 'R lung'
    contourToAddShift = targetContourToUse

    # interfraction changes parameters
    baselineShift = [-2, 0, 0]
    translation = [-20, 0, 10]
    rotation = [0, 5, 0]
    shrinkSize = [3, 3, 3]

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
    ax[0].imshow(GTVMaskCopy.imageArray[:, GTVCenterOfMassInVoxels[1], :], alpha=0.5)
    ax[0].set_title('Initial image and target mask')
    ax[1].imshow(shrinkedDynMod.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[1].imshow(shrinkedOrganMask.imageArray[:, GTVCenterOfMassInVoxels[1], :], alpha=0.5)
    ax[1].set_title('after inter fraction changes')
    ax[2].imshow(dynModCopy.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :] - shrinkedDynMod.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[2].set_title('image difference')
    ax[3].imshow(GTVMaskCopy.imageArray[:, GTVCenterOfMassInVoxels[1], :] ^ shrinkedOrganMask.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[3].set_title('mask difference')
    plt.show()

    ## to save the model with inter fraction changes applied
    # saveSerializedObjects(patient, savingPath + 'interFracChanged_ModelAndROIs')