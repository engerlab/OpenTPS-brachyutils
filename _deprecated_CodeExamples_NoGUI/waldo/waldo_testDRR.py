import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
import matplotlib.pyplot as plt
import numpy as np
import concurrent
# from timeit import repeat

import time

from opentps_core.opentps.core import computeDRRSet, forwardProjection
from opentps_core.opentps.core.IO import loadDataStructure

if __name__ == '__main__':

    # multiprocessing.set_start_method('spawn')
    organ = 'lung'
    patientFolder = 'Patient_4'
    patientComplement = '/1/FDG1'
    basePath = '/DATA2/public/'

    resultFolder = '/test4/'
    resultDataFolder = 'data/'

    dataPath = basePath + organ  + '/' + patientFolder + patientComplement + '/test4/croppedModelAndROIs.p'

    patient = loadDataStructure(dataPath)[0]
    dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct = patient.getPatientDataOfType("RTStruct")[0]

    ## use the forward projection directly on an image with an angle of 0
    img = dynMod.midp

    numberOfsamples = 30
    globalTime = time.time()
    for i in range(numberOfsamples):
        startTime = time.time()
        DRR = forwardProjection(img, 0, axis='Z')
        stopTime = time.time()
        print(stopTime-startTime)

    print(np.round((time.time() - globalTime)/numberOfsamples, 2), 'per sample')

    angles = np.linspace(0, 360, numberOfsamples)
    print(angles)
    print(angles.shape)

    imgList = [img for i in range(numberOfsamples)]
    print(len(imgList))
    axisList = ['Z' for i in range(numberOfsamples)]
    print(len(axisList))

    globalTime2 = time.time()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = executor.map(forwardProjection, imgList, angles, axisList)
    
    print(np.round((time.time() - globalTime2)/numberOfsamples, 2), 'per sample')

    plt.figure()
    plt.imshow(DRR)
    plt.show()

    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    ## use it on a CTImage with 3 angles, then get back a list of DRR that can be added to a patient
    anglesAndAxisList = [[0, 'Z'],
                        [30, 'X'],
                        [-10, 'Y']]


    DRRSet = computeDRRSet(dynMod.midp, anglesAndAxisList)
    
    for DRRImage in DRRSet:
        print(DRRImage.name)
    
    plt.figure()
    plt.subplot(1, 3, 1)
    plt.imshow(DRRSet[0].imageArray)
    plt.subplot(1, 3, 2)
    plt.imshow(DRRSet[1].imageArray)
    plt.subplot(1, 3, 3)
    plt.imshow(DRRSet[2].imageArray)
    plt.show()
    
    print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    ## try the DRR Set in multi processing
    AAList =  [anglesAndAxisList for i in range(numberOfsamples)]
    globalTime3 = time.time()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = executor.map(computeDRRSet, imgList, AAList)
    
    print(np.round((time.time() - globalTime3)/numberOfsamples, 2), 'per sample')


