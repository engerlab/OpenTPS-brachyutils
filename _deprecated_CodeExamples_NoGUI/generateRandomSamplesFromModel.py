import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
from pathlib import Path
import time
import numpy as np
import matplotlib.pyplot as plt

from opentps_core.opentps.core.IO import loadDataStructure
from opentps_core.opentps.core.Processing import generateRandomImagesFromModel, generateRandomDeformationsFromModel

if __name__ == '__main__':

    testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

    ## read a serialized dynamic sequence
    dataPath = testDataPath + "veryLightDynMod.p"
    dynMod = loadDataStructure(dataPath)[0]

    tryGPU = True
    numberOfSamples = 50

    imageList = []

    startTime = time.time()

    defList = generateRandomDeformationsFromModel(dynMod, numberOfSamples=numberOfSamples, ampDistribution='gaussian')
    for deformation in defList:
        imageList.append(deformation.deformData(dynMod.midp, fillValue='closest', tryGPU=tryGPU))

    print(len(imageList))
    print('first test done in ', np.round(time.time() - startTime, 2))

    plt.figure()
    plt.imshow(imageList[0].imageArray[:, 50, :])
    plt.show()

    startTime = time.time()
    imageList = generateRandomImagesFromModel(dynMod, numberOfSamples=numberOfSamples, ampDistribution='gaussian', tryGPU=tryGPU)
    print('second test done in ', np.round(time.time() - startTime, 2))

    plt.figure()
    plt.imshow(imageList[0].imageArray[:, 50, :])
    plt.show()