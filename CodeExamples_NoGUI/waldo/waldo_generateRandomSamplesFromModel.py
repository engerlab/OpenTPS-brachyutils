import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
from pathlib import Path
import cProfile
import time
import numpy as np
import concurrent
import matplotlib.pyplot as plt

from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Processing.DeformableDataAugmentationToolBox.generateRandomSamplesFromModel import generateRandomImagesFromModel, generateRandomDeformationsFromModel

if __name__ == '__main__':

    organ = 'lung'
    patientFolder = 'Patient_4'
    patientComplement = '/1/FDG1'
    basePath = '/DATA2/public/'

    resultFolder = '/testCupy/'
    resultDataFolder = 'data/'

    dataPath = basePath + organ  + '/' + patientFolder + patientComplement + '/dynModAndROIs.p'
    savingPath = basePath + organ  + '/' + patientFolder + patientComplement + resultFolder

    if not os.path.exists(savingPath):
        os.umask(0)
        os.makedirs(savingPath)  # Create a new directory because it does not exist
        os.makedirs(savingPath + resultDataFolder)  # Create a new directory because it does not exist
        print("New directory created to save the data: ", savingPath)

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