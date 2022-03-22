"""
This file contains an example on how to:
- read data from a 4DCT folder
- create a dynamic 3D sequence with the 4DCT data
- save this sequence in serialized format in drive
"""
import os
from pathlib import Path

from Core.IO.dataLoader import loadAllData
from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.IO.serializedObjectIO import saveSerializedObjects

# Get the current working directory, its parent, then add the testData folder at the end of it
testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

## read a serialized dynamic sequence
dataPath = testDataPath + "4DCTDicomLight"
dataList = loadAllData(dataPath)
print(len(dataList), 'images found in the folder')
print('Image type =', type(dataList[0]))

## create a Dynamic3DSequence and change its name
dynseq = Dynamic3DSequence(dyn3DImageList=dataList)
print('Type of the created object =', type(dynseq))
print('Sequence name =', dynseq.name)
dynseq.name = 'new4DCT'
print('Sequence name = ', dynseq.name)
print('Sequence lenght =', len(dynseq.dyn3DImageList))

## save it as a serialized object
# savingPath = testDataPath + 'TestSmall_dynSeq'
# saveSerializedObjects(dynseq, savingPath)
