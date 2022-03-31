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
from Core.Processing.ImageProcessing.imageFilter2D import getBinaryMaskFromROIDRR, get2DMaskCenterOfMass
import multiprocessing
import concurrent


def deformImageTest(img, deformation, deformationIndex):

    print('Deforming image ', deformationIndex)
    image = deformation.deformImage(img, fillValue='closest', outputType=np.int16)

    print('Projection image ', deformationIndex)
    DRR = forwardProjection(image, 0, axis='X')
    # print('Projection mask ', deformationIndex)
    # DRRMask = forwardProjection(mask, 0, axis='X')
    # binaryDRRMask = getBinaryMaskFromROIDRR(DRRMask)
    # centerOfMass = get2DMaskCenterOfMass(binaryDRRMask)
    #
    return 0


dataPath = '/home/damien/Desktop/Patient0/Patient0BaseAndMod_Velocity.p'
patient = loadDataStructure(dataPath)[0]

dynSeq = patient.getPatientDataOfType("Dynamic3DSequence")[0]
dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
rtStruct = patient.getPatientDataOfType("RTStruct")[0]

# # -----------------------------------------
# if dynMod.deformationList[0].displacement == None:
#     print('Compute displacement fields')
#     for fieldIndex, field in enumerate(dynMod.deformationList):
#         print(fieldIndex)
#         field.displacement = field.velocity.exponentiateField()
#
# savingPath = '/home/damien/Desktop/Patient0/Patient0BaseAndMod_Velocity'
# saveSerializedObjects(patient, savingPath)
#
# print('--------------- ggggggggggggggggggggggg')
#
# # ----------------------------------------------------



## get the ROI and mask on which we want to apply the motion signal
print('Available ROIs')
rtStruct.print_ROINames()
gtvContour = rtStruct.get_contour_by_name('MidP CT GTV')
ROIMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)

## get the center of mass of this ROI
gtvCenterOfMass = gtvContour.getCenterOfMass(dynMod.midp.origin, dynMod.midp.gridSize, dynMod.midp.spacing)
print('Used ROI name and center of mass :', gtvContour.name, gtvCenterOfMass)

## to get amplitude from model !!! it takes some time
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
                                     samplingPeriod=0.2,
                                     simulationTime=7,
                                     meanEvent=1/30)

newSignal.generateBreathingSignal()

sequenceSize = newSignal.breathingSignal.shape[0]
subSequenceSize = 8
print('Sequence Size =', sequenceSize, 'split by stack of ', subSequenceSize)

subSequencesIndexes = [subSequenceSize * i for i in range(math.ceil(sequenceSize/subSequenceSize))]
subSequencesIndexes.append(sequenceSize)
print(subSequencesIndexes)

# plt.figure()
# plt.plot(newSignal.timestamps, newSignal.breathingSignal)
# plt.xlabel("Time [s]")
# plt.ylabel("Amplitude [mm]")
# plt.title("Breathing signal")
# # for index in subSequencesIndexes:
# #     plt.vlines(index)
# # plt.xlim((0, 50))
# plt.show()

centerOfMassList = []

for i in range(len(subSequencesIndexes)-1):
    print('Creating deformations for images from', subSequencesIndexes[i], 'to', subSequencesIndexes[i + 1] - 1)

    deformationList = generateDeformationListFromBreathingSignalsAndModel(dynMod,
                                                                          [newSignal.breathingSignal],
                                                                          [gtvCenterOfMass],
                                                                          signalIdxUsed=[subSequencesIndexes[i], subSequencesIndexes[i+1]],
                                                                          dimensionUsed='Z',
                                                                          outputType=np.float32)

    imageList = []
    maskList = []

    processes = []
    for deformationIndex, deformation in enumerate(deformationList):

        p = multiprocessing.Process(target=deformImageTest, args=[dynMod.midp, deformation, deformationIndex])
        p.start()
        processes.append(p)

        # print('Deforming image ', deformationIndex)
        # image = deformation.deformImage(dynMod.midp, fillValue='closest', outputType=np.int16)
        # print('Deforming mask ', deformationIndex)
        # mask = deformation.deformImage(ROIMask, fillValue='closest')
        #
        # print('Projection image ', deformationIndex)
        # DRR = forwardProjection(image, 0, axis='X')
        # print('Projection mask ', deformationIndex)
        # DRRMask = forwardProjection(mask, 0, axis='X')
        # binaryDRRMask = getBinaryMaskFromROIDRR(DRRMask)
        # centerOfMass = get2DMaskCenterOfMass(binaryDRRMask)
        #
        # print('centerOfMass', centerOfMass)

        # imageList.append(DRR)
        # maskList.append(binaryDRRMask)
        # centerOfMassList.append(centerOfMass)

        # plt.figure()
        # plt.subplot(1, 3, 1)
        # plt.imshow(DRR)
        # plt.subplot(1, 3, 2)
        # plt.imshow(DRRMask)
        # plt.subplot(1, 3, 3)
        # plt.imshow(binaryDRRMask)
        # plt.show()

    for proc in processes:
        proc.join()

    savingPath = '/home/damien/Desktop/' + 'Patient0_DRRAndMasks_part' + str(i)
    saveSerializedObjects([imageList, maskList], savingPath)



dynSeq.breathingPeriod = newSignal.breathingPeriod
dynSeq.timingsList = newSignal.timestamps*1000

print(type(dynSeq.dyn3DImageList[0].imageArray[0, 0, 0]))

## save it as a serialized object
# savingPath = '/home/damien/Desktop/' + 'PatientTest_InvLung'
# saveSerializedObjects(dynSeq, savingPath)


