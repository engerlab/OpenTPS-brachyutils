from Core.IO.dicomReader import readDicomCT
from Core.IO.dataLoader import listAllFiles, loadAllData
from Core.IO.serializedObjectIO import saveSerializedObject

## option 1 specific to dicoms
dataPath = ""
filesList = listAllFiles(dataPath)
print(filesList)
image1 = readDicomCT(filesList['Dicom'])
print(type(image1))

## option 2 general
dataList = loadAllData(dataPath)
img2 = dataList[0]
print(type(img2)) ## print the type of the first element

## save data as serialized object
savingPath = '/home/damien/Desktop/' + 'PatientTest_CT.p'
saveSerializedObject(img2, savingPath)