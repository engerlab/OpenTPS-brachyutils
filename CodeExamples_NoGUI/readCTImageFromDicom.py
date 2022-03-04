"""
This file contains an example on how to:
- read a 3D CT image from a folder
- change its name and print its grid size and pixel spacing
- show a slice
"""

from Core.IO.dicomReader import readDicomCT
from Core.IO.dataLoader import listAllFiles, loadAllData
from Core.IO.serializedObjectIO import saveSerializedObjects
import matplotlib.pyplot as plt
import os
from pathlib import Path

# Get the current working directory, its parent, then add the testData folder at the end of it
testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')
ctImagePath = testDataPath + "4DCTDicomLight/00"

## option 1 specific to dicoms
filesList = listAllFiles(ctImagePath)
print(filesList)
image1 = readDicomCT(filesList['Dicom'])
print(type(image1))

## option 2 general
dataList = loadAllData(ctImagePath)
img2 = dataList[0]
print(type(img2))

print(img2.name)
img2.name = 'newImage'
print(img2.name)
print(img2.gridSize, img2.spacing)

plt.figure()
plt.imshow(img2.imageArray[:,:,int(img2.gridSize[2]/2)])
plt.show()
