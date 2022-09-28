"""
This file contains an example on how to:
- read data from a 4DCT folder
- create a dynamic 3D sequence with the 4DCT data
- save this sequence in serialized format in drive
"""
import os
from pathlib import Path
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)

from opentps_core.opentps.core.IO import readData
from opentps_core.opentps.core.data import Dynamic3DSequence
from opentps_core.opentps.core.IO import saveSerializedObjects

if __name__ == '__main__':

    # Get the current working directory, its parent, then add the testData folder at the end of it
    testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

    ## read a serialized dynamic sequence
    dataPath = testDataPath + "4DCTDicomLight"

    print(dataPath)
    dataList = readData(dataPath)
    print(len(dataList), 'images found in the folder')
    print('Image type =', type(dataList[0]))

    ## create a Dynamic3DSequence and change its name
    dynseq = Dynamic3DSequence(dyn3DImageList=dataList)
    print('Type of the created object =', type(dynseq))
    print('Sequence name =', dynseq.name)
    dynseq.name = 'Light4DCT'
    print('Sequence name = ', dynseq.name)
    print('Sequence lenght =', len(dynseq.dyn3DImageList))

    # save it as a serialized object
    savingPath = testDataPath + 'lightDynSeq'
    saveSerializedObjects(dynseq, savingPath)
