"""
This file contains an example on how to:
- read a 3D CT image from a folder
- change its name and print its grid size and pixel spacing
- show a slice
"""

import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
import matplotlib.pyplot as plt
from pathlib import Path

from opentps_core.opentps.core.IO import readDicomCT
from opentps_core.opentps.core.IO import listAllFiles, readData

if __name__ == '__main__':

    # Get the current working directory, its parent, then add the testData folder at the end of it
    testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')
    ctImagePath = testDataPath + "4DCTDicomLight/00"

    ## option 1 specific to dicoms
    filesList = listAllFiles(ctImagePath)
    print(filesList)
    image1 = readDicomCT(filesList['Dicom'])
    print(type(image1))

    ## option 2 general
    dataList = readData(ctImagePath)
    img2 = dataList[0]
    print(type(img2))

    print(img2.name)
    img2.name = 'newImage'
    print(img2.name)
    print(img2.gridSize, img2.spacing)

    plt.figure()
    plt.imshow(img2.imageArray[:,:,int(img2.gridSize[2]/2)])
    plt.show()
