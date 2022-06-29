"""
This file contains an example on how to:
- read model + ROI data from a serialized file
- create a breathing signal using the motion amplitude present in the model
- chose an ROI to apply the breathing signal to its center of mass
-

!!! does not work with public data for now since there is no struct in the public data !!!
"""

import matplotlib.pyplot as plt
import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
import math
import time

from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Processing.ImageProcessing.howToNameThisFile import *
from Core.Processing.ImageSimulation.multiProcForkMethods import multiProcDRRs

if __name__ == '__main__':


    # data and paths selection--------------------------------- 
    organ = 'lung'
    patientFolder = 'Patient_5'
    patientComplement = '/1/FDG1'
    basePath = '/DATA2/public/'

    resultFolder = '/test7/'
    resultDataFolder = 'data/'

    # parameters selection ------------------------------------
    outputSize = [64, 64]
    deleteDataSourceFiles = False

    # use Z - 0 for Coronal and Z - 90 for sagittal
    projAngle = 0
    projAxis = 'Z'

    maxMultiProcUse = 10
    ## ---------------------------------------------------------


    ## path management -------------------
    dataPath = basePath + organ  + '/' + patientFolder + patientComplement + resultFolder + resultDataFolder
    savingPath = basePath + organ  + '/' + patientFolder + patientComplement + resultFolder

    if not os.path.exists(savingPath):
        os.umask(0)
        os.makedirs(savingPath)  # Create a new directory because it does not exist
        os.makedirs(savingPath + resultDataFolder)  # Create a new directory because it does not exist
        print("New directory created to save the data: ", savingPath)


    ## files sorting--------------------------------------
    filesList = os.listdir(dataPath)
    print(len(filesList), 'Files found in the folder')

    filesListToRMIdx = []
    for fileElementIndex, fileElement in enumerate(filesList):
        if 'DRR' in fileElement:
            print('File name', fileElement, ' already contains "DRR". This might be an inapropriate file to apply this script and is removed from the list.')
            filesListToRMIdx.append(fileElementIndex)

    filesListToRMIdx.reverse()
    for idx in filesListToRMIdx:
        del filesList[idx]

    print('Used files list:')
    for fileName in filesList:
        print('-', fileName)

    ## applying script goals -------------------------------------------
    totalImgCount = 0
    startTime = time.time()

    for fileIndex, fileElement in enumerate(filesList):
        
        imgAndMaskDRRsPlus2DAnd3DCOMs = []
        dataList = loadDataStructure(dataPath + fileElement)
        
        sequenceSize = len(dataList)
        totalImgCount += sequenceSize
        print('Sequence Size =', sequenceSize)

        multiProcIndexes = [maxMultiProcUse * j for j in range(math.ceil(sequenceSize / maxMultiProcUse))]
        multiProcIndexes.append(len(dataList))
        print('MultiProcIndexes', multiProcIndexes)

        for z in range(len(multiProcIndexes) -1 ):
            print('Creating DRR for images', multiProcIndexes[z], 'to', multiProcIndexes[z + 1] - 1)

            imgAndMaskDRRsPlus2DAnd3DCOMs += multiProcDRRs(dataList[multiProcIndexes[z]: multiProcIndexes[z+1]], projAngle, projAxis, outputSize)

            if fileIndex == 0 and z == 0:
                plt.figure()
                plt.imshow(imgAndMaskDRRsPlus2DAnd3DCOMs[-1][0])
                plt.imshow(imgAndMaskDRRsPlus2DAnd3DCOMs[-1][1], alpha=0.5)
                plt.savefig(savingPath + 'test.pdf', dpi=300)
                plt.show()

            print('ResultList lenght', len(imgAndMaskDRRsPlus2DAnd3DCOMs))

        for elementIndex in range(len(dataList)):
            imgAndMaskDRRsPlus2DAnd3DCOMs[elementIndex].append(dataList[elementIndex][2])

        imgIndexes = fileElement.split('_')[1:3]
        imgIndexes[1] = imgIndexes[1].split('.')[0]

        savingPathTemp = savingPath + resultDataFolder + 'ImgMasksDRRsPlus2DAnd3DCOMs_' + imgIndexes[0] + '_' + imgIndexes[1]
        saveSerializedObjects(imgAndMaskDRRsPlus2DAnd3DCOMs, savingPathTemp)

        if deleteDataSourceFiles:
            os.remove(dataPath + fileElement)

    stopTime = time.time()
    print('Script with multiprocessing. Sequence size:', totalImgCount, 'finished in', np.round(stopTime - startTime, 2) / 60, 'minutes')
    print(np.round((stopTime - startTime) / totalImgCount, 2), 'sec per sample')

    