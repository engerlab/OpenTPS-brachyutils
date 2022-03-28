"""
This file contains an example on how to:
- read a serialized dynamic 3D sequence
- create a dynamic 3D model with the dynamic 3D sequence
- save the model in serialized format in drive
"""

from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.IO.serializedObjectIO import saveSerializedObjects
from Core.Data.DynamicData.dynamic3DModel import Dynamic3DModel
from Core.IO.serializedObjectIO import loadDataStructure
import os
from pathlib import Path
from pydicom.uid import generate_uid
import time
import numpy as np

# Get the current working directory, its parent, then add the testData folder at the end of it
testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

## read a serialized dynamic sequence
dataPath = testDataPath + "lightDynSeq.p"
dynSeq = loadDataStructure(dataPath)[0]

print(type(dynSeq))
print(len(dynSeq.dyn3DImageList), 'images in the dynamic sequence')

## create Dynamic3DModel
model3D = Dynamic3DModel()

## change its name
model3D.name = 'MidP'

## give it an seriesInstanceUID
model3D.seriesInstanceUID = generate_uid()

## generate the midP image and deformation fields from a dynamic 3D sequence
startTime = time.time()
model3D.computeMidPositionImage(dynSeq, tryGPU=True)
stopTime = time.time()

print('midP computed in ', np.round(stopTime-startTime))

# ## save it as a serialized object
# savingPath = testDataPath + 'Test_dynMod'
# saveSerializedObjects(model3D, savingPath)