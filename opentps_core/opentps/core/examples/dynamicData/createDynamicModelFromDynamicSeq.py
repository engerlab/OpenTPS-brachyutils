"""
This file contains an example on how to:
- read a serialized dynamic 3D sequence
- create a dynamic 3D model with the dynamic 3D sequence
- save the model in serialized format in drive
"""

import os
import sys

from opentps.core.data.dynamicData.dynamic3DModel import Dynamic3DModel
from opentps.core.io.serializedObjectIO import loadDataStructure, saveSerializedObjects
from pydicom.uid import generate_uid
import time
import numpy as np
import logging
from opentps.core._loggingConfig import configure

currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
os.chdir(currentWorkingDir)

logger = logging.getLogger(__name__)

if __name__ == '__main__':

    options = configure(sys.argv[1:])

    # Get the current working directory, its parent, then add the testData folder at the end of it
    testDataPath = os.path.join(currentWorkingDir, 'testData')

    ## read a serialized dynamic sequence
    dataPath = testDataPath + "lightDynSeq.p"
    dynSeq = loadDataStructure(dataPath)[0]
    dynSeq.dyn3DImageList = dynSeq.dyn3DImageList[::2]

    print(type(dynSeq))
    print(len(dynSeq.dyn3DImageList), 'images in the dynamic sequence')

    # reduce resolution to speed up calculations
    dynSeq.resample(np.array([5, 5, 5]), None, None)

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

    ## save it as a serialized object
    savingPath = testDataPath + 'Test_dynMod'
    saveSerializedObjects(model3D, savingPath)