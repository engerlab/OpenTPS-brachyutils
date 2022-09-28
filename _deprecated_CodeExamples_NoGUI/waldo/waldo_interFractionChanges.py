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

if __name__ == '__main__':

    organ = 'lung'
    patientFolder = 'Patient_12'
    patientComplement = '/1/FDG1'
    basePath = '/DATA2/public/'

    resultFolder = '/test10/'
    resultDataFolder = 'data/'

    dataPath = basePath + organ  + '/' + patientFolder + patientComplement + '/dynModAndROIs.p'#'/dynModAndROIs_bodyCropped.p'
    savingPath = basePath + organ  + '/' + patientFolder + patientComplement + resultFolder

    # parameters selection ------------------------------------
    bodyContourToUse = 'patient'
    targetContourToUse = 'gtv t'
    lungContourToUse = 'r lung'
    contourToAddShift = targetContourToUse

    # interfraction changes parameters
    baselineShift = [0, 0, 0]
    translation = [0, 0, 0]
    rotation = [0, 0, 0]
    shrinkSize = [3, 3, 3]

    # GPU used
    usedGPU = 1

    try:
        import cupy
        cupy.cuda.Device(usedGPU).use()
    except:
        print('Module Cupy not found')

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
        dynModCopy, GTVMaskCopy = applyBaselineShift(dynModCopy, GTVMaskCopy, baselineShift)
    else:
        print('Not implemented in this script --> must use the get contour by name function')

    print('-' * 50)
    translateData(dynModCopy, translationInMM=translation)
    translateData(GTVMaskCopy, translationInMM=translation)

    print('-'*50)
    rotateData(dynModCopy, rotationInDeg=rotation)
    rotateData(GTVMaskCopy, rotationInDeg=rotation)

    print('-' * 50)
    dynModCopy, GTVMaskCopy, newMask3DCOM = shrinkOrgan(dynModCopy, GTVMaskCopy, shrinkSize=shrinkSize)
    #shrinkedDynMod.name = 'MidP_ShrinkedGTV'

    print('-' * 50)

    stopTime = time.time()
    print('time:', stopTime-startTime)


    fig, ax = plt.subplots(1, 4)
    fig.suptitle('Example of baseline shift, translate, rotate and shrink')
    ax[0].imshow(dynMod.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[0].imshow(GTVMask.imageArray[:, GTVCenterOfMassInVoxels[1], :], alpha=0.5)
    ax[0].set_title('Initial image and target mask')
    ax[1].imshow(dynModCopy.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[1].imshow(GTVMaskCopy.imageArray[:, GTVCenterOfMassInVoxels[1], :], alpha=0.5)
    ax[1].set_title('after inter fraction changes')
    ax[2].imshow(dynMod.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :] - dynModCopy.midp.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[2].set_title('image difference')
    ax[3].imshow(GTVMask.imageArray[:, GTVCenterOfMassInVoxels[1], :] ^ GTVMaskCopy.imageArray[:, GTVCenterOfMassInVoxels[1], :])
    ax[3].set_title('mask difference')
    plt.show()