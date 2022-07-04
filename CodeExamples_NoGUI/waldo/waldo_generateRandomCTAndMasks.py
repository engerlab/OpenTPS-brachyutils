import os
import time
import numpy as np
import matplotlib.pyplot as plt
import sys
sys.path.append('..')
from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure
from Core.Processing.DeformableDataAugmentationToolBox.generateRandomSamplesFromModel import generateRandomImagesFromModel, generateRandomDeformationsFromModel
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import *
from Core.Processing.ImageProcessing.segmentation3D import *

## Load patient & dynModCroppedXY
patientName = 'Patient_5'
dataComplement = '/1/FDG1/'
fileName = 'dynModCroppedXY.p'
dataCropPath = '/DATA2/public/lung/' + patientName + dataComplement + fileName
dynModCrop = loadDataStructure(dataCropPath)[0]

patientPath = '/DATA2/public/lung/' + patientName + dataComplement + 'dynModAndROIs.p'
patient = loadDataStructure(patientPath)[0]
rtStruct = patient.getPatientDataOfType("RTStruct")[0]


savingPath = '/DATA2/eloyen/lungNEW/' + patientName + dataComplement
fileNameImage = 'NewRandom3DCT-ListE'
fileNameMask = 'NewRandomMask-ListE'

## Get the mask of the GTV (in the cropped dimensions)
print('Available ROIs')
rtStruct.print_ROINames()
gtvContour = rtStruct.getContourByName('GTV T')
GTVMask = gtvContour.getBinaryMask(origin=dynModCrop.midp.origin, gridSize=dynModCrop.midp.gridSize, spacing=dynModCrop.midp.spacing)
print(type(GTVMask.imageArray))

## Generate random deformations
imageList = []
maskList = []
defList = generateRandomDeformationsFromModel(dynModCrop, numberOfSamples=300, amplitudeRange=[0.6, 1.3], ampDistribution='gaussian')
i = 0
iter = 0
for deformation in defList:
    print("deformation", i)
    i = i + 1
    imageList.append(deformation.deformImage(dynModCrop.midp, fillValue='closest', tryGPU=True))
    maskList.append(deformation.deformImage(GTVMask, fillValue='closest', tryGPU=True))
    if i == 100:
        if not os.path.exists(savingPath):
            os.umask(0)
            os.makedirs(savingPath)  # Create a new directory because it does not exist
            print("New directory created to save the data: ", savingPath)
        saveSerializedObjects(imageList, savingPath + fileNameImage + str(iter))
        saveSerializedObjects(maskList, savingPath + fileNameMask + str(iter))
        imageList = []
        maskList = []
        i = 0
        iter = iter + 1




print('saved in:', savingPath + fileNameImage)