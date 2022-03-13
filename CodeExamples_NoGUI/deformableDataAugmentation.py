from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
import matplotlib.pyplot as plt
from Core.Data.DynamicData.breathingSignals import SyntheticBreathingSignal
from Core.Processing.DeformableDataAugmentationToolBox.generateDynamicSequencesFromModel import generateDynSeqFromBreathingSignalsAndModel
import numpy as np
import os
from pathlib import Path
import math

testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

## read a serialized dynamic sequence
# dataPath = '/home/damien/Desktop/Patient0/Patient0BaseAndMod.p'
dataPath = testDataPath + "superLightDynSeqWithMod.p"
patient = loadDataStructure(dataPath)[0]

dynSeq = patient.getPatientDataOfType("Dynamic3DSequence")[0]
dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]

simulationTime = 10
amplitude = 15

newSignal = SyntheticBreathingSignal(amplitude=amplitude,
                                     variationAmplitude=0,
                                     breathingPeriod=4,
                                     variationFrequency=0,
                                     shift=0,
                                     mean=0,
                                     variance=0,
                                     samplingPeriod=0.2,
                                     simulationTime=simulationTime,
                                     meanEvent=0/30)

newSignal.generateBreathingSignal()
linearIncrease = np.linspace(0.8, 10, newSignal.breathingSignal.shape[0])

newSignal.breathingSignal = newSignal.breathingSignal * linearIncrease

newSignal2 = SyntheticBreathingSignal(amplitude=amplitude,
                                     variationAmplitude=0,
                                     breathingPeriod=4,
                                     variationFrequency=0,
                                     shift=0,
                                     mean=0,
                                     variance=0,
                                     samplingPeriod=0.2,
                                     simulationTime=simulationTime,
                                     meanEvent=0/30)

newSignal2.breathingSignal = -newSignal.breathingSignal

signalList = [newSignal.breathingSignal, newSignal2.breathingSignal]

#time, samples = signal(amplitude, dA, period, df, dS, step, signalDuration, L)
plt.figure()
plt.plot(newSignal.timestamps, newSignal.breathingSignal)
plt.plot(newSignal.timestamps, newSignal2.breathingSignal)
plt.xlabel("Time [s]")
plt.ylabel("Amplitude [mm]")
plt.title("Breathing signal")
# plt.xlim((0, 50))
plt.show()

pointLLung = np.array([-94, 45, -117])
pointRLung = np.array([108, 72, -116])

pointList = [pointRLung, pointLLung]

## all in one seq version
dynSeq = generateDynSeqFromBreathingSignalsAndModel(dynMod, signalList, pointList, dimensionUsed='Z', outputType=np.int16)
dynSeq.breathingPeriod = newSignal.breathingPeriod
dynSeq.timingsList = newSignal.timestamps*1000

## save it as a serialized object
savingPath = '/home/damien/Desktop/' + 'PatientTest_InvLung'
saveSerializedObjects(dynSeq, savingPath)

print('/'*80, '\n', '/'*80)

## by signal sub part version
sequenceSize = newSignal.breathingSignal.shape[0]
subSequenceSize = 6
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
    dynSeq.timingsList = newSignal.timestamps[subSequencesIndexes[i]:subSequencesIndexes[i+1]] * 1000

    ## save it as a serialized object
    savingPath = '/home/damien/Desktop/' + 'PatientTest_InvLung_part' + str(i)
    saveSerializedObjects(dynSeq, savingPath)