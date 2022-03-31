## Data come from : https://www.creatis.insa-lyon.fr/rio/popi-model_original_page

from Core.IO.dataLoader import loadAllData
from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.Data.patient import Patient
from Core.IO.serializedObjectIO import saveSerializedObjects
from Core.Data.DynamicData.dynamic3DModel import Dynamic3DModel
import numpy as np
import matplotlib.pyplot as plt


## read a 4DCT
dataPath = "/home/damien/Desktop/4DCT-Dicom"
dataList = loadAllData(dataPath)
print(len(dataList))
print(type(dataList[0]))

## create a Dynamic3DSequence and change its name
dynseq = Dynamic3DSequence(dyn3DImageList=dataList, name='testSeq')
print(dynseq.name)
dynseq.name = 'new4DCT'
print(dynseq.name)

print(len(dynseq.dyn3DImageList))
print(type(dynseq.dyn3DImageList[0]))

# testArray  = dynseq.dyn3DImageList[0].imageArray
print('before resampling', dynseq.dyn3DImageList[0].origin, dynseq.dyn3DImageList[0].spacing, dynseq.dyn3DImageList[0].gridSize)
print(np.min(dynseq.dyn3DImageList[0].imageArray), np.max(dynseq.dyn3DImageList[0].imageArray))
#resizeFactor =
plt.figure()
plt.imshow(dynseq.dyn3DImageList[0].imageArray[:,:,70])
plt.show()
# new_array = zoom(testArray, (0.5, 0.5, 1))
# print(np.min(new_array), np.max(new_array))
gridSizeAfterResample = [100, 100, 60]
spacingAfterResample = [dynseq.dyn3DImageList[0].spacing[0] * (dynseq.dyn3DImageList[0].gridSize[0]/gridSizeAfterResample[0]),
                        dynseq.dyn3DImageList[0].spacing[1] * (dynseq.dyn3DImageList[0].gridSize[1]/gridSizeAfterResample[1]),
                        dynseq.dyn3DImageList[0].spacing[2] * (dynseq.dyn3DImageList[0].gridSize[2]/gridSizeAfterResample[2])]
print('spacingAfterResample', spacingAfterResample)

for image in dynseq.dyn3DImageList:
    image.resample(gridSizeAfterResample, dynseq.dyn3DImageList[0].origin, spacingAfterResample)
    image.imageArray = image.imageArray.astype(np.int16)

print('after resampling', dynseq.dyn3DImageList[0].origin, dynseq.dyn3DImageList[0].spacing, dynseq.dyn3DImageList[0].gridSize)
print(np.min(dynseq.dyn3DImageList[0].imageArray), np.max(dynseq.dyn3DImageList[0].imageArray))
print(type(dynseq.dyn3DImageList[0].imageArray[0, 0, 0]))
# plt.figure()
# plt.imshow(dynseq.dyn3DImageList[0].imageArray[:,:,45])
# plt.show()

savingPath = "/home/damien/Desktop/lightTest4DCT"
saveSerializedObjects(dynseq, savingPath)

Model4D = Dynamic3DModel()
Model4D.computeMidPositionImage(dynseq, baseResolution=8)

patient = Patient()
patient.appendPatientData(dynseq)
patient.appendPatientData(Model4D)

savingPath = "/home/damien/Desktop/lightTest4DCTWithMod"
saveSerializedObjects(patient, savingPath)