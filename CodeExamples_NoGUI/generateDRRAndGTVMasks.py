"""
This file contains an example on how to:
- read model + ROI data from a serialized file
- create a breathing signal using the motion amplitude present in the model
- chose an ROI to apply the breathing signal to its center of mass
-

!!! does not work with public data for now since there is no struct in the public data !!!
"""

from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
import matplotlib.pyplot as plt
from Core.Data.DynamicData.breathingSignals import SyntheticBreathingSignal
from Core.Processing.DeformableDataAugmentationToolBox.generateDynamicSequencesFromModel import generateDeformationListFromBreathingSignalsAndModel
import numpy as np
import os
from pathlib import Path
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import *
import math
from Core.Processing.DRRToolBox import computeDRRSet, forwardProjection
from Core.Processing.ImageProcessing.image2DManip import getBinaryMaskFromROIDRR, get2DMaskCenterOfMass
import concurrent
from itertools import repeat
import time
from Core.Processing.ImageProcessing.crop3D import *
import cProfile

# pr = cProfile.Profile()
# pr.enable()

patientFolder = 'Patient_0'
dataSetFolder = '/test/'
dataSetDataFolder = 'data/'
dataPath = '/home/damien/Desktop/' + patientFolder + '/dynModAndROIs.p'
savingPath = f'/home/damien/Desktop/' + patientFolder + dataSetFolder

if not os.path.exists(savingPath):
    os.makedirs(savingPath)   # Create a new directory because it does not exist
    os.makedirs(savingPath + dataSetDataFolder)  # Create a new directory because it does not exist
    print("New directory created to save the data: ", savingPath)

sequenceDurationInSecs = 150
samplingFrequency = 4
subSequenceSize = 12

multiprocessing = True
maxMultiProcUse = 8
tryGPU = True

projAngle = 0
projAxis = 'Z'

## ------------------------------------------------------------------------------------
def deformImageAndMaskAndComputeDRRs(img, ROIMask, deformation, projectionAngle=0, projectionAxis='Z', tryGPU=True):
    """
    This function is specific to this example and used to :
    - deform a CTImage and an ROIMask,
    - create DRR's for both,
    - binarize the DRR of the ROIMask
    - compute its center of mass
    """

    print('Start deformations and projections for deformation', deformation.name)
    image = deformation.deformImage(img, fillValue='closest', outputType=np.int16, tryGPU=tryGPU)
    mask = deformation.deformImage(ROIMask, fillValue='closest', outputType=np.int16, tryGPU=tryGPU)

    DRR = forwardProjection(image, projectionAngle, axis=projectionAxis)
    DRRMask = forwardProjection(mask, projectionAngle, axis=projectionAxis)

    halfDiff = int((DRR.shape[1] - image.gridSize[2])/2)           ## not sure this will work if orientation is changed
    croppedDRR = DRR[:, halfDiff + 1:DRR.shape[1] - halfDiff - 1]         ## not sure this will work if orientation is changed
    croppedDRRMask = DRRMask[:, halfDiff + 1:DRRMask.shape[1] - halfDiff - 1] ## not sure this will work if orientation is changed

    binaryDRRMask = getBinaryMaskFromROIDRR(croppedDRRMask)
    centerOfMass = get2DMaskCenterOfMass(binaryDRRMask)
    # print('CenterOfMass:', centerOfMass)

    del image  # to release the RAM
    del mask  # to release the RAM

    print('Deformations and projections finished for deformation', deformation.name)

    # plt.figure()
    # plt.subplot(1, 5, 1)
    # plt.imshow(DRR)
    # plt.subplot(1, 5, 2)
    # plt.imshow(croppedDRR)
    # plt.subplot(1, 5, 3)
    # plt.imshow(DRRMask)
    # plt.subplot(1, 5, 4)
    # plt.imshow(croppedDRRMask)
    # plt.subplot(1, 5, 5)
    # plt.imshow(binaryDRRMask)
    # plt.show()

    return [croppedDRR, binaryDRRMask, centerOfMass]
## ------------------------------------------------------------------------------------


patient = loadDataStructure(dataPath)[0]
dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
rtStruct = patient.getPatientDataOfType("RTStruct")[0]

## get the ROI and mask on which we want to apply the motion signal
print('Available ROIs')
rtStruct.print_ROINames()

gtvContour = rtStruct.getContourByName('MidP CT GTV')
GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)
gtvBox = getBoxAroundROI(GTVMask)

## get the body contour to adjust the crop in the direction of the DRR projection
bodyContour = rtStruct.getContourByName('body')
bodyMask = bodyContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)
bodyBox = getBoxAroundROI(bodyMask)

croppingBox = [gtvBox[0], bodyBox[1], gtvBox[2]] ## create the used box combining the two boxes

## crop the model data using the box
marginInMM = 40 ## seems well suited for liver Patient_0
crop3DDataAroundBox(dynMod, croppingBox, marginInMM=[marginInMM, 0, marginInMM*2.5])

## get the mask in cropped version (the dynMod.midp is now cropped so its origin and gridSize has changed)
GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)

## if you want to see the crop in the GUI you can save the data in cropped version
saveSerializedObjects(patient, savingPath + 'Test_Cropped')

## get the 3D center of mass of this ROI
gtvCenterOfMass = gtvContour.getCenterOfMass(dynMod.midp.origin, dynMod.midp.gridSize, dynMod.midp.spacing)
gtvCenterOfMassInVoxels = getVoxelIndexFromPosition(gtvCenterOfMass, dynMod.midp)
print('Used ROI name', gtvContour.name)
print('Used ROI center of mass :', gtvCenterOfMass)
print('Used ROI center of mass in voxels:', gtvCenterOfMassInVoxels)

## to get amplitude from model !!! it takes some time because 10 displacement fields must be computed just for this
modelValues = getAverageModelValuesAroundPosition(gtvCenterOfMass, dynMod, dimensionUsed='Z')
amplitude = np.max(modelValues) - np.min(modelValues)
print('Amplitude of deformation at ROI center of mass', amplitude)

## Signal creation
newSignal = SyntheticBreathingSignal(amplitude=amplitude,
                                     variationAmplitude=2,
                                     breathingPeriod=4,
                                     variationFrequency=0.1,
                                     shift=2,
                                     meanNoise=0,
                                     varianceNoise=0.5,
                                     samplingPeriod=1/samplingFrequency,
                                     simulationTime=sequenceDurationInSecs,
                                     meanEvent=2/30)

newSignal.generateBreathingSignal()

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
    ax = plt.subplot(2, len(pointList), pointIndex+1)
    ax.set_title('Slice Y:' + str(pointList[pointIndex][1]))
    ax.imshow(np.rot90(dynMod.midp.imageArray[:, pointVoxelList[pointIndex][1], :]))
    ax.scatter([pointVoxelList[pointIndex][0]], [dynMod.midp.imageArray.shape[2] - pointVoxelList[pointIndex][2]], c=colors[pointIndex], marker="x", s=100)
    signalAx.plot(newSignal.timestamps/1000, signalList[pointIndex], c=colors[pointIndex])

signalAx.set_xlabel('Time (s)')
signalAx.set_ylabel('Deformation amplitude in Z direction (mm)')
plt.savefig(savingPath + 'ROI_And_Signals_fig.pdf', dpi=300)
plt.show()

## -------------------------------------------------------------

sequenceSize = newSignal.breathingSignal.shape[0]
print('Sequence Size =', sequenceSize, 'split by stack of ', subSequenceSize, '. Multiprocessing =', multiprocessing)

subSequencesIndexes = [subSequenceSize * i for i in range(math.ceil(sequenceSize/subSequenceSize))]
subSequencesIndexes.append(sequenceSize)
print('Sub sequences indexes', subSequencesIndexes)

startTime = time.time()

if multiprocessing == False:

    resultList = []

    for i in range(len(subSequencesIndexes)-1):
        print('Creating deformations for images', subSequencesIndexes[i], 'to', subSequencesIndexes[i + 1] - 1)

        deformationList = generateDeformationListFromBreathingSignalsAndModel(dynMod,
                                                                              signalList,
                                                                              pointList,
                                                                              signalIdxUsed=[subSequencesIndexes[i], subSequencesIndexes[i+1]],
                                                                              dimensionUsed='Z',
                                                                              outputType=np.float32)

        for deformationIndex, deformation in enumerate(deformationList):
            resultList.append(deformImageAndMaskAndComputeDRRs(dynMod.midp,
                                                               GTVMask,
                                                               deformation,
                                                               projectionAngle=projAngle,
                                                               projectionAxis=projAxis,
                                                               tryGPU=True))


    savingPath += dataSetDataFolder + f'Patient_0_{sequenceSize}_DRRMasksAndCOM'
    saveSerializedObjects(resultList, savingPath + str(sequenceSize))


elif multiprocessing == True:

    resultList = []

    if subSequenceSize > maxMultiProcUse:  ## re-adjust the subSequenceSize since this will be done in multi processing
        subSequenceSize = maxMultiProcUse
        print('SubSequenceSize put to', maxMultiProcUse, 'for multiprocessing.')
        print('Sequence Size =', sequenceSize, 'split by stack of ', subSequenceSize, '. Multiprocessing =', multiprocessing)
        subSequencesIndexes = [subSequenceSize * i for i in range(math.ceil(sequenceSize / subSequenceSize))]
        subSequencesIndexes.append(sequenceSize)

    for i in range(len(subSequencesIndexes)-1):
        print('Creating deformations for images', subSequencesIndexes[i], 'to', subSequencesIndexes[i + 1] - 1)

        deformationList = generateDeformationListFromBreathingSignalsAndModel(dynMod,
                                                                              signalList,
                                                                              pointList,
                                                                              signalIdxUsed=[subSequencesIndexes[i], subSequencesIndexes[i+1]],
                                                                              dimensionUsed='Z',
                                                                              outputType=np.float32)

        print('Start multi process deformation with', len(deformationList), 'deformations')
        with concurrent.futures.ProcessPoolExecutor() as executor:

            results = executor.map(deformImageAndMaskAndComputeDRRs, repeat(dynMod.midp), repeat(GTVMask), deformationList, repeat(projAngle), repeat(projAxis), repeat(tryGPU))
            resultList += results

        print('ResultList lenght', len(resultList))

    savingPath += dataSetDataFolder + f'Patient_0_{sequenceSize}_DRRMasksAndCOM_multiProcTest'
    saveSerializedObjects(resultList, savingPath)

stopTime = time.time()
print('Test with multiprocessing =', multiprocessing, '. Sub-sequence size:', str(subSequenceSize), 'finished in', np.round(stopTime - startTime, 2) / 60, 'minutes')
print(np.round((stopTime - startTime)/len(resultList), 2), 'sec per sample')