"""
This file contains an example on how to:
- read data from a 4DCT folder
- create a dynamic 3D sequence with the 4DCT data
- create a dynamic 3D model with the dynamic 3D sequence
- save these objects in serialized format in drive
"""
from Core.IO.dataLoader import loadAllData
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.IO.serializedObjectIO import saveSerializedObject
from Core.Data.dynamic3DModel import Dynamic3DModel
from pydicom.uid import generate_uid

## read a 4DCT
dataList = loadAllData("/media/damien/data/ImageData/Liver/Patient0/4DCT/")
print(len(dataList))
print(type(dataList[0]))

## create a Dynamic3DSequence and change its name
dynseq = Dynamic3DSequence(dyn3DImageList=dataList)
print(type(dynseq))
print(dynseq.name, dynseq.breathingPeriod)
dynseq.name = 'new4DCT'
print(dynseq.name)
print(len(dynseq.dyn3DImageList))
print(type(dynseq.dyn3DImageList[0]))

## save it as a serialized object
savingPath = '/home/damien/Desktop/' + 'PatientTest_dynSeq.p'
saveSerializedObject(dynseq, savingPath)

## create Dynamic3DModel
newMod = Dynamic3DModel()
newMod.name = 'MidP'
newMod.seriesInstanceUID = generate_uid()
newMod.computeMidPositionImage(dynseq)

## save it as a serialized object
savingPath = '/home/damien/Desktop/' + 'PatientTest_dynMod.p'
saveSerializedObject(newMod, savingPath)