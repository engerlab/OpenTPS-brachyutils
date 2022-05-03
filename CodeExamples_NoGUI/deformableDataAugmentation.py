import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
import numpy as np
from pathlib import Path
import math

from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
import matplotlib.pyplot as plt
from Core.Data.DynamicData.breathingSignals import SyntheticBreathingSignal
from Core.Processing.DeformableDataAugmentationToolBox.generateDynamicSequencesFromModel import generateDynSeqFromBreathingSignalsAndModel
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import getVoxelIndexFromPosition

if __name__ == '__main__':

    testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

    ## read a serialized dynamic sequence
    # dataPath = '/home/damien/Desktop/Patient0/Patient0BaseAndMod.p'
    dataPath = testDataPath + "superLightDynSeqWithMod.p"
    patient = loadDataStructure(dataPath)[0]

    dynSeq = patient.getPatientDataOfType("Dynamic3DSequence")[0]
    dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]

    simulationTime = 32
    amplitude = 10

    newSignal = SyntheticBreathingSignal(amplitude=amplitude,
                                         variationAmplitude=0,
                                         breathingPeriod=4,
                                         variationFrequency=0,
                                         shift=0,
                                         meanNoise=0,
                                         varianceNoise=0,
                                         samplingPeriod=0.2,
                                         meanEvent=0/30,
                                         simulationTime=simulationTime,
                                         )

    newSignal.generate1DBreathingSignal()
    linearIncrease = np.linspace(0.8, 10, newSignal.breathingSignal.shape[0])

    newSignal.breathingSignal = newSignal.breathingSignal * linearIncrease

    newSignal2 = SyntheticBreathingSignal(amplitude=amplitude,
                                         variationAmplitude=0,
                                         breathingPeriod=4,
                                         variationFrequency=0,
                                         shift=0,
                                         meanNoise=0,
                                         varianceNoise=0,
                                         samplingPeriod=0.2,
                                         simulationTime=simulationTime,
                                         meanEvent=0/30)

    newSignal2.breathingSignal = -newSignal.breathingSignal

    signalList = [newSignal.breathingSignal, newSignal2.breathingSignal]
    # signalList = [newSignal.breathingSignal] ## for single ROI testing

    pointRLung = np.array([108, 72, -116])
    pointLLung = np.array([-94, 45, -117])

    ## get points in voxels --> for the plot, not necessary for the process example
    pointRLungInVoxel = getVoxelIndexFromPosition(pointRLung, dynMod.midp)
    pointLLungInVoxel = getVoxelIndexFromPosition(pointLLung, dynMod.midp)

    pointList = [pointRLung, pointLLung]
    # pointList = [pointRLung] ## for single ROI testing
    pointVoxelList = [pointRLungInVoxel, pointLLungInVoxel]
    # pointVoxelList = [pointRLungInVoxel] ## for single ROI testing

    ## to show signals and ROIs
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']
    plt.figure(figsize=(12, 6))
    signalAx = plt.subplot(2, 1, 2)
    for pointIndex, point in enumerate(pointList):
        ax = plt.subplot(2, 2 * len(pointList), 2 * pointIndex + 1)
        ax.set_title('Slice Y:' + str(pointVoxelList[pointIndex][1]))
        ax.imshow(np.rot90(dynMod.midp.imageArray[:, pointVoxelList[pointIndex][1], :]))
        ax.scatter([pointVoxelList[pointIndex][0]], [dynMod.midp.imageArray.shape[2] - pointVoxelList[pointIndex][2]],
                   c=colors[pointIndex], marker="x", s=100)
        ax2 = plt.subplot(2, 2 * len(pointList), 2 * pointIndex + 2)
        ax2.set_title('Slice Z:' + str(pointVoxelList[pointIndex][2]))
        ax2.imshow(np.rot90(dynMod.midp.imageArray[:, :, pointVoxelList[pointIndex][2]], 3))
        ax2.scatter([pointVoxelList[pointIndex][0]], [pointVoxelList[pointIndex][1]],
                   c=colors[pointIndex], marker="x", s=100)
        signalAx.plot(newSignal.timestamps / 1000, signalList[pointIndex], c=colors[pointIndex])
 
    signalAx.set_xlabel('Time (s)')
    signalAx.set_ylabel('Deformation amplitude in Z direction (mm)')
    plt.show()


    ## all in one seq version
    dynSeq = generateDynSeqFromBreathingSignalsAndModel(dynMod, signalList, pointList, dimensionUsed='Z', outputType=np.int16)
    dynSeq.breathingPeriod = newSignal.breathingPeriod
    dynSeq.timingsList = newSignal.timestamps


    ## save it as a serialized object
    savingPath = 'C:/Users/damie/Desktop/' + 'PatientTest_InvLung'
    saveSerializedObjects(dynSeq, savingPath)

    print('/'*80, '\n', '/'*80)


    ## by signal sub part version
    sequenceSize = newSignal.breathingSignal.shape[0]
    subSequenceSize = 25
    print('Sequence Size =', sequenceSize, 'split by stack of ', subSequenceSize)

    subSequencesIndexes = [subSequenceSize * i for i in range(math.ceil(sequenceSize/subSequenceSize))]
    subSequencesIndexes.append(sequenceSize)
    print('Sub sequences indexes', subSequencesIndexes)

    for i in range(len(subSequencesIndexes)-1):
        print('*'*80)
        print('Creating images', subSequencesIndexes[i], 'to', subSequencesIndexes[i + 1] - 1)
        dynSeq = generateDynSeqFromBreathingSignalsAndModel(dynMod,
                                                            signalList,
                                                            pointList,
                                                            signalIdxUsed=[subSequencesIndexes[i], subSequencesIndexes[i+1]],
                                                            dimensionUsed='Z',
                                                            outputType=np.int16)

        dynSeq.breathingPeriod = newSignal.breathingPeriod
        dynSeq.timingsList = newSignal.timestamps[subSequencesIndexes[i]:subSequencesIndexes[i+1]]

        ## save it as a serialized object
        savingPath = 'C:/Users/damie/Desktop/' + 'PatientTest_InvLung_part' + str(i)
        saveSerializedObjects(dynSeq, savingPath)