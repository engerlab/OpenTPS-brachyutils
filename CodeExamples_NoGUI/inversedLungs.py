
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Data.dynamic3DModel import Dynamic3DModel
from pydicom.uid import generate_uid
import matplotlib.pyplot as plt
from Core.Processing.BreathingSignalGeneration import signal
from Core.Data.breathingSignalData import SyntheticBreathingSignal

import os
from pathlib import Path

testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

## read a serialized dynamic sequence
dataPath = testDataPath + "lightTest4DCT.p"
dynSeq = loadDataStructure(dataPath)[0]
print(type(dynSeq))
print(len(dynSeq.dyn3DImageList))
print(type(dynSeq.dyn3DImageList[0]))

"""
## generate a breathing signal
#parametres changeables
A = 10 #amplitude (mm)
dA = 2 #variation d amplitude possible (mm)
T = 4.0 #periode respiratoire (s)
df = 0 #variation de frequence possible (Hz)
dS = 0 #shift du signal (mm)
step = 0.2 #periode d echantillonnage
Tend = 100 #temps de simulation
L = 2/30 #moyenne des evenements aleatoires
"""
newSignal = SyntheticBreathingSignal()
newSignal.generateBreathingSignal()

#time, samples = signal(A, dA, T, df, dS, step, Tend, L)
plt.figure()
plt.plot(newSignal.timestamps, newSignal.breathingSignal)
plt.xlabel("Time [s]")
plt.ylabel("Amplitude [mm]")
plt.title("Breathing signal")
# plt.xlim((0, 50))
plt.show()