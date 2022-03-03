
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Data.dynamic3DModel import Dynamic3DModel
from pydicom.uid import generate_uid
import matplotlib.pyplot as plt
from Core.Processing.BreathingSignalGeneration import signal
from Core.Data.breathingSignalData import SyntheticBreathingSignal
from Core.Processing.ImageProcessing.generateSequenceFromSignalsAndPoints import generateDynSeqFromBreathingSignalsROIsAndModel
import numpy as np
import os
from pathlib import Path

testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

## read a serialized dynamic sequence
dataPath = testDataPath + "lightTest4DCTWithMod.p"
patient = loadDataStructure(dataPath)[0]

dynSeq = patient.getPatientDataOfType("Dynamic3DSequence")[0]
dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]

simulationTime = 30
amplitude = 10

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

linearIncrease = np.linspace(0.8, 4, newSignal.breathingSignal.shape[0])

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

#time, samples = signal(A, dA, T, df, dS, step, Tend, L)
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

dynSeq = generateDynSeqFromBreathingSignalsROIsAndModel(dynMod, signalList, pointList, dimensionUsed='Z', outputType=np.int16)
dynSeq.breathingPeriod = newSignal.breathingPeriod
print('we should use ms as default time unit everywhere --> to change in breathing signal generation')
dynSeq.timingsList = newSignal.timestamps*1000

print(type(dynSeq.dyn3DImageList[0].imageArray[0,0,0]))

## save it as a serialized object
savingPath = '/home/damien/Desktop/' + 'PatientTest_InvLung'
saveSerializedObjects(dynSeq, savingPath)