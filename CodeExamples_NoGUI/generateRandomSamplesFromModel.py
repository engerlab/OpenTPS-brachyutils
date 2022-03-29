from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Processing.DeformableDataAugmentationToolBox.generateRandomSamplesFromModel import generateRandomImagesFromModel, generateRandomDeformationsFromModel
import os
from pathlib import Path
import cProfile
import time
import numpy as np
import concurrent
import matplotlib.pyplot as plt

if __name__ == '__main__':

    testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

    ## read a serialized dynamic sequence
    dataPath = testDataPath + "superLightDynSeqWithMod.p"
    # dataPath = '/home/damien/Desktop/Patient0/Patient0_Model_bodyCropped.p'
    patient = loadDataStructure(dataPath)[0]
    dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]


    imageList = []

    startTime = time.time()

    defList = generateRandomDeformationsFromModel(dynMod, numberOfSamples=10, ampDistribution='gaussian')
    for deformation in defList:
        imageList.append(deformation.deformImage(dynMod.midp, fillValue='closest', tryGPU=True))

    print(len(imageList))
    print('first test done in ', np.round(time.time() - startTime, 2))

    plt.figure()
    plt.imshow(imageList[0].imageArray[:, 50, :])
    plt.show()

    startTime = time.time()
    imageList = generateRandomImagesFromModel(dynMod, numberOfSamples=10, ampDistribution='gaussian', tryGPU=True)
    print('second test done in ', np.round(time.time() - startTime, 2))

    plt.figure()
    plt.imshow(imageList[0].imageArray[:, 50, :])
    plt.show()