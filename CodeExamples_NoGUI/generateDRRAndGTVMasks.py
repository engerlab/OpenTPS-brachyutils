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
dataPath = '/home/damien/Desktop/' + patientFolder + '/dynModAndROIs.p'
savingPath = f'/home/damien/Desktop/' + patientFolder + '/'

sequenceDurationInSecs = 10
samplingFrequency = 2
subSequenceSize = 10
multiprocessing = True
tryGPU = True


## ------------------------------------------------------------------------------------
def deformImageAndMaskAndComputeDRRs(img, ROIMask, deformation, tryGPU=True):

    print('Start deformations and projections for deformation', deformation.name)
    image = deformation.deformImage(img, fillValue='closest', outputType=np.int16, tryGPU=tryGPU)
    mask = deformation.deformImage(ROIMask, fillValue='closest', outputType=np.int16, tryGPU=tryGPU)

    DRR = forwardProjection(image, 0)
    DRRMask = forwardProjection(mask, 0)
    binaryDRRMask = getBinaryMaskFromROIDRR(DRRMask)
    centerOfMass = get2DMaskCenterOfMass(binaryDRRMask)
    # print('CenterOfMass:', centerOfMass)

    del image  # to release the RAM
    del mask  # to release the RAM

    print('Deformations and projections finished for deformation', deformation.name)

    # plt.figure()
    # plt.subplot(1, 3, 1)
    # plt.imshow(np.rot90(DRR))
    # plt.subplot(1, 3, 2)
    # plt.imshow(np.rot90(DRRMask))
    # plt.subplot(1, 3, 3)
    # plt.imshow(np.rot90(binaryDRRMask))
    # plt.show()

    return [DRR, binaryDRRMask, centerOfMass]
## ------------------------------------------------------------------------------------


patient = loadDataStructure(dataPath)[0]
dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
rtStruct = patient.getPatientDataOfType("RTStruct")[0]

## get the ROI and mask on which we want to apply the motion signal
print('Available ROIs')
rtStruct.print_ROINames()

gtvContour = rtStruct.get_contour_by_name('MidP CT GTV')
GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)
gtvBox = getBoxAroundROI(GTVMask)

bodyContour = rtStruct.get_contour_by_name('body')
bodyMask = bodyContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)
bodyBox = getBoxAroundROI(bodyMask)

marginInMM = 50

gtvBox[1] = bodyBox[1]
crop3DDataAroundBox(dynMod, gtvBox, marginInMM=[marginInMM, 0, marginInMM])
GTVMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)

## to see the crop in the GUI
saveSerializedObjects(patient, savingPath + 'Test_Cropped')
# savingPath = '/home/damien/Desktop/' + 'Test_dynMod_Cropped'
# saveSerializedObjects(dynMod, savingPath)

## get the center of mass of this ROI
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
                                     variationAmplitude=0.5,
                                     breathingPeriod=4,
                                     variationFrequency=0,
                                     shift=0,
                                     mean=0,
                                     variance=0.5,
                                     samplingPeriod=1/samplingFrequency,
                                     simulationTime=sequenceDurationInSecs,
                                     meanEvent=1/30)

newSignal.generateBreathingSignal()

pointList = [gtvCenterOfMass]
pointVoxelList = [gtvCenterOfMassInVoxels]
signalList = [newSignal.breathingSignal]


## to show signals and ROIs --> maybe save this figure with the resulting data to show which signal is applied where (for presentations or papers for example)
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
        print('Creating deformations for images from', subSequencesIndexes[i], 'to', subSequencesIndexes[i + 1])

        deformationList = generateDeformationListFromBreathingSignalsAndModel(dynMod,
                                                                              signalList,
                                                                              pointList,
                                                                              signalIdxUsed=[subSequencesIndexes[i], subSequencesIndexes[i+1]],
                                                                              dimensionUsed='Z',
                                                                              outputType=np.float32)

        for deformationIndex, deformation in enumerate(deformationList):
            # print('Deforming image ', deformationIndex)
            # image = deformation.deformImage(dynMod.midp, fillValue='closest', outputType=np.int16, tryGPU=tryGPU)
            # print('Deforming mask ', deformationIndex)
            # mask = deformation.deformImage(ROIMask, fillValue='closest', tryGPU=tryGPU)
            #
            # print('Projection image ', deformationIndex)
            # DRR = forwardProjection(image, 0, axis='X')
            # print('Projection mask ', deformationIndex)
            # DRRMask = forwardProjection(mask, 0, axis='X')
            # binaryDRRMask = getBinaryMaskFromROIDRR(DRRMask)
            # centerOfMass = get2DMaskCenterOfMass(binaryDRRMask)
            # # print('centerOfMass', centerOfMass)
            #
            # del image #to release the RAM
            # del mask #to release the RAM

            resultList.append(deformImageAndMaskAndComputeDRRs(dynMod.midp, GTVMask, deformation, tryGPU=True))


    savingPath = f'/home/damien/Desktop/Patient0_{sequenceSize}_DRRMasksAndCOM'
    saveSerializedObjects(resultList, savingPath + str(sequenceSize))

    print('Test with multiprocessing =', multiprocessing, 'finished in', np.round(time.time()-startTime, 2))

elif multiprocessing == True:

    resultList = []

    if subSequenceSize > 6:  ## re-adjust the subSequenceSize since this will be done in multi processing
        subSequenceSize = 6
        print('SubSequenceSize put to 4 for multiprocessing.')
        print('Sequence Size =', sequenceSize, 'split by stack of ', subSequenceSize, '. Multiprocessing =', multiprocessing)
        subSequencesIndexes = [subSequenceSize * i for i in range(math.ceil(sequenceSize / subSequenceSize))]
        subSequencesIndexes.append(sequenceSize)

    for i in range(len(subSequencesIndexes)-1):
        print('Creating deformations for images from', subSequencesIndexes[i], 'to', subSequencesIndexes[i + 1])

        deformationList = generateDeformationListFromBreathingSignalsAndModel(dynMod,
                                                                              signalList,
                                                                              pointList,
                                                                              signalIdxUsed=[subSequencesIndexes[i], subSequencesIndexes[i+1]],
                                                                              dimensionUsed='Z',
                                                                              outputType=np.float32)

        print('Start multi process deformation with', len(deformationList), 'deformations')
        with concurrent.futures.ProcessPoolExecutor() as executor:

            results = executor.map(deformImageAndMaskAndComputeDRRs, repeat(dynMod.midp), repeat(GTVMask), deformationList, repeat(tryGPU))
            resultList += results

        print('resultList lenght', len(resultList))

    savingPath = f'/home/damien/Desktop/Patient0_{sequenceSize}_DRRMasksAndCOM_multiProcTest'
    saveSerializedObjects(resultList, savingPath)

    print('Test with multiprocessing =', multiprocessing, 'and sub-sequence size:', str(subSequenceSize), 'finished in', np.round(time.time() - startTime, 2))