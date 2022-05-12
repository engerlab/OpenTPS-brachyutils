"""
This file contains an example on how to:
- read model + ROI data from a serialized file
- chose using ROIs a cropping box to crop the model data
- create a breathing signal using the motion amplitude present in the model
- chose an ROI to apply the breathing signal to its center of mass
- deform the model image to follow the breathing signal
- save the generated images by part

!!! does not work with public data for now since there is no struct in the public data !!!
"""

import matplotlib.pyplot as plt
import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
from scipy.ndimage import zoom
import math
import time

from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Data.DynamicData.breathingSignals import SyntheticBreathingSignal
from Core.Processing.DeformableDataAugmentationToolBox.generateDynamicSequencesFromModel import generateDeformationListFromBreathingSignalsAndModel
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import *
from Core.Processing.ImageProcessing.crop3D import *
from CodeExamples_NoGUI.waldo.multiProcSpawnMethods import multiProcDeform

if __name__ == '__main__':


    ## defining data paths -------------------- 
    organ = 'lung'
    patientFolder = 'Patient_5'
    patientComplement = '/1/FDG1'
    basePath = '/DATA2/public/'

    resultFolder = '/test7/'
    resultDataFolder = 'data/'

    dataPath = basePath + organ  + '/' + patientFolder + patientComplement + '/dynModAndROIs.p'
    savingPath = basePath + organ  + '/' + patientFolder + patientComplement + resultFolder

    # parameters selection ------------------------------------
    sequenceDurationInSecs = 2
    samplingFrequency = 4
    subSequenceSize = 50
    
    bodyContourToUse = 'Body'
    targetContourToUse = 'GTV T'

    croppingContoursUsedXYZ = [targetContourToUse, bodyContourToUse, targetContourToUse]
    isBoxHardCoded = False
    hardCodedBox = [[88, 451], [79, 322], [20, 157]]
    marginInMM = [30, 5, 30]

    projAngle = 0
    projAxis = 'Z'

    # breathing signal parameters
    amplitude = 'model'
    variationAmplitude = 0.5
    breathingPeriod = 4
    variationFrequency = 0.1
    shift = 0.5
    meanNoise = 0
    varianceNoise = 0.1
    samplingPeriod = 1 / samplingFrequency
    simulationTime = sequenceDurationInSecs
    meanEvent = 2 / 30

    maxMultiProcUse = 14

    ## Script start -------------------------------------------------------------
    
    if not os.path.exists(savingPath):
        os.umask(0)
        os.makedirs(savingPath)  # Create a new directory because it does not exist
        os.makedirs(savingPath + resultDataFolder)  # Create a new directory because it does not exist
        print("New directory created to save the data: ", savingPath)

    patient = loadDataStructure(dataPath)[0]
    dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct = patient.getPatientDataOfType("RTStruct")[0]

    ## get the ROI and mask on which we want to apply the motion signal
    print('Available ROIs')
    rtStruct.print_ROINames()

    gtvContour = rtStruct.getContourByName(targetContourToUse)
    GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize,
                                       spacing=dynMod.midp.spacing)
    gtvBox = getBoxAroundROI(GTVMask)

    ## get the body contour to adjust the crop in the direction of the DRR projection
    bodyContour = rtStruct.getContourByName(bodyContourToUse)
    bodyMask = bodyContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize,
                                         spacing=dynMod.midp.spacing)
    bodyBox = getBoxAroundROI(bodyMask)
    print('Body Box from contour', bodyBox)

    croppingBox = [[], [], []]
    for i in range(3):
        if croppingContoursUsedXYZ[i] == bodyContourToUse:
            croppingBox[i] = bodyBox[i]
        elif croppingContoursUsedXYZ[i] == targetContourToUse:
            croppingBox[i] = gtvBox[i]

    ## crop the model data using the box
    crop3DDataAroundBox(dynMod, croppingBox, marginInMM=marginInMM)

    ## get the mask in cropped version (the dynMod.midp is now cropped so its origin and gridSize has changed)
    GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize,
                                       spacing=dynMod.midp.spacing)

    ## if you want to see the crop in the GUI you can save the data in cropped version
    saveSerializedObjects(patient, savingPath + 'croppedModelAndROIs')

    ## get the 3D center of mass of this ROI
    gtvCenterOfMass = gtvContour.getCenterOfMass(dynMod.midp.origin, dynMod.midp.gridSize, dynMod.midp.spacing)
    gtvCenterOfMassInVoxels = getVoxelIndexFromPosition(gtvCenterOfMass, dynMod.midp)
    print('Used ROI name', gtvContour.name)
    print('Used ROI center of mass :', gtvCenterOfMass)
    print('Used ROI center of mass in voxels:', gtvCenterOfMassInVoxels)

    if amplitude == 'model':
        ## to get amplitude from model !!! it takes some time because 10 displacement fields must be computed just for this
        modelValues = getAverageModelValuesAroundPosition(gtvCenterOfMass, dynMod, dimensionUsed='Z')
        amplitude = np.max(modelValues) - np.min(modelValues)
        print('Amplitude of deformation at ROI center of mass', amplitude)

    ## Signal creation
    newSignal = SyntheticBreathingSignal(amplitude=amplitude,
                                         variationAmplitude=variationAmplitude,
                                         breathingPeriod=breathingPeriod,
                                         variationFrequency=variationFrequency,
                                         shift=shift,
                                         meanNoise=meanNoise,
                                         varianceNoise=varianceNoise,
                                         samplingPeriod=samplingPeriod,
                                         simulationTime=sequenceDurationInSecs,
                                         meanEvent=meanEvent)

    newSignal.generate1DBreathingSignal()

    pointList = [gtvCenterOfMass]
    pointVoxelList = [gtvCenterOfMassInVoxels]
    signalList = [newSignal.breathingSignal]

    saveSerializedObjects([signalList, pointList], savingPath + 'ROIsAndSignalObjects')

    ## to show signals and ROIs
    ## -------------------------------------------------------------
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']
    plt.figure(figsize=(12, 6))
    signalAx = plt.subplot(2, 1, 2)

    for pointIndex, point in enumerate(pointList):
        ax = plt.subplot(2, 2 * len(pointList), 2 * pointIndex + 1)
        ax.set_title('Slice Y:' + str(pointVoxelList[pointIndex][1]))
        ax.imshow(np.rot90(dynMod.midp.imageArray[:, pointVoxelList[pointIndex][1], :]))
        ax.imshow(np.rot90(GTVMask.imageArray[:, pointVoxelList[pointIndex][1], :]), alpha=0.3)
        ax.scatter([pointVoxelList[pointIndex][0]], [dynMod.midp.imageArray.shape[2] - pointVoxelList[pointIndex][2]],
                   c=colors[pointIndex], marker="x", s=100)
        ax2 = plt.subplot(2, 2 * len(pointList), 2 * pointIndex + 2)
        ax2.set_title('Slice Z:' + str(pointVoxelList[pointIndex][2]))
        ax2.imshow(np.rot90(dynMod.midp.imageArray[:, :, pointVoxelList[pointIndex][2]]))
        ax2.imshow(np.rot90(GTVMask.imageArray[:, :, pointVoxelList[pointIndex][2]]), alpha=0.3)
        ax2.scatter([pointVoxelList[pointIndex][0]], [pointVoxelList[pointIndex][1]],
                   c=colors[pointIndex], marker="x", s=100)
        signalAx.plot(newSignal.timestamps / 1000, signalList[pointIndex], c=colors[pointIndex])

    signalAx.set_xlabel('Time (s)')
    signalAx.set_ylabel('Deformation amplitude in Z direction (mm)')
    plt.savefig(savingPath + 'ROI_And_Signals_fig.pdf', dpi=300)
    plt.show()

    ## -------------------------------------------------------------

    sequenceSize = newSignal.breathingSignal.shape[0]
    print('Sequence Size =', sequenceSize, 'split by stack of ', subSequenceSize, '. Multiprocessing =', maxMultiProcUse)

    subSequencesIndexes = [subSequenceSize * i for i in range(math.ceil(sequenceSize / subSequenceSize))]
    subSequencesIndexes.append(sequenceSize)
    print('Sub sequences indexes', subSequencesIndexes)

    startTime = time.time()
    
    for i in range(len(subSequencesIndexes) - 1):

        resultList = []

        multiProcIndexes = [subSequencesIndexes[i] + maxMultiProcUse * j for j in range(math.ceil((subSequencesIndexes[i+1] - subSequencesIndexes[i]) / maxMultiProcUse))]
        multiProcIndexes.append(subSequencesIndexes[i+1])
        print('MultiProcIndexes', multiProcIndexes)

        for z in range(len(multiProcIndexes) -1 ):
            print('Creating deformations for images', multiProcIndexes[z], 'to', multiProcIndexes[z + 1] - 1)

            deformationList = generateDeformationListFromBreathingSignalsAndModel(dynMod,
                                                                                    signalList,
                                                                                    pointList,
                                                                                    signalIdxUsed=[multiProcIndexes[z], multiProcIndexes[z + 1]],
                                                                                    dimensionUsed='Z',
                                                                                    outputType=np.float32)

            print('Start multi process deformation with', len(deformationList), 'deformations')
            
            resultList += multiProcDeform(deformationList, dynMod, GTVMask)

            if i == 0 and z == 0:
                plt.figure()
                plt.imshow(resultList[-1][0].imageArray[:,:,50])
                plt.imshow(resultList[-1][1].imageArray[:,:,50], alpha=0.5)
                plt.savefig(savingPath + 'test.pdf', dpi=300)

            print('ResultList lenght', len(resultList))

        savingPathTemp = savingPath + resultDataFolder + 'ImgMasksAndCOM_' + str(subSequencesIndexes[i]) + '_' + str(subSequencesIndexes[i+1])
        saveSerializedObjects(resultList, savingPathTemp)

    stopTime = time.time()
    print('Script with multiprocessing. Sequence size:', sequenceSize, 'finished in', np.round(stopTime - startTime, 2) / 60, 'minutes')
    print(np.round((stopTime - startTime) / sequenceSize, 2), 'sec per sample')