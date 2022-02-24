from Core.IO.dicomReader import readDicomCT
from Core.IO.dataLoader import listAllFiles, loadAllData
from Core.IO.serializedObjectIO import saveSerializedObjects
import matplotlib.pyplot as plt

## option 1 specific to dicoms
dataPath = "/media/damien/data/ImageData/Liver/Patient0/4DCT/p30"
filesList = listAllFiles(dataPath)
print(filesList)
image1 = readDicomCT(filesList['Dicom'])
print(type(image1))

## option 2 general
dataList = loadAllData(dataPath)
img2 = dataList[0]
print(type(img2)) ## print the type of the first element

# plt.figure()
# plt.imshow(img2.imageArray[:,:,100])
# plt.show()

## save data as serialized object
savingPath = '/home/damien/Desktop/' + 'PatientTest_CT.p'
saveSerializedObjects(img2, savingPath)