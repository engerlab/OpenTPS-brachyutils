import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
import matplotlib.pyplot as plt
from pathlib import Path

from opentps_core.opentps.core import computeDRRSet, computeDRRSequence, forwardProjection, createDRRDynamic2DSequences
from opentps_core.opentps.core.IO import saveSerializedObjects
from opentps_core.opentps.core.IO import readData
from opentps_core.opentps.core.data import Dynamic3DSequence
from opentps_core.opentps.core.data._patient import Patient

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
    dynSeq = Dynamic3DSequence(dyn3DImageList=dataList)
    print('Type of the created object =', type(dynSeq))
    print('Sequence name =', dynSeq.name)
    dynSeq.name = 'new4DCT'
    print('Sequence name = ', dynSeq.name)
    print('Sequence lenght =', len(dynSeq.dyn3DImageList))

    # use the forward projection directly on an image with an angle of 0
    img = dynSeq.dyn3DImageList[0]
    DRR = forwardProjection(img, 90, axis='X')

    plt.figure()
    plt.imshow(DRR)
    plt.show()

    print('!!!!!!!!!!!!!!! forwardProjection example end !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    ## use it on a CTImage with 3 angles, then get back a list of DRR that can be added to a patient
    anglesAndAxisList = [[0, 'Z'],
                        [30, 'X'],
                        [-10, 'Y']]

    # anglesAndAxisList = [[0, 'Z']]

    DRRSet = computeDRRSet(dynSeq.dyn3DImageList[0], anglesAndAxisList)

    for DRRImage in DRRSet:
        print(type(DRRImage), DRRImage.name)

    plt.figure()
    plt.subplot(1, 3, 1)
    plt.imshow(DRRSet[0].imageArray)
    plt.subplot(1, 3, 2)
    plt.imshow(DRRSet[1].imageArray)
    plt.subplot(1, 3, 3)
    plt.imshow(DRRSet[2].imageArray)
    plt.show()

    print('!!!!!!!!!!!!!!!!!!computeDRRSet example end!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    ## use it on a sequence, then get back a list of DRR that can be added to a patient
    DRRSequence = computeDRRSequence(dynSeq, anglesAndAxisList)

    for DRRSet in DRRSequence:
        print('-----------')
        for DRRImage in DRRSet:
            print(DRRImage.name)

    plt.figure()
    plt.subplot(1, 3, 1)
    plt.imshow(DRRSequence[0][1].imageArray)
    plt.subplot(1, 3, 2)
    plt.imshow(DRRSequence[5][1].imageArray)
    plt.subplot(1, 3, 3)
    plt.imshow(DRRSequence[2][0].imageArray)
    plt.show()

    print('!!!!!!!!!!!!!!!!!!!!computeDRRSequence example end!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    ## create dynamic 2D sequences of DRR's
    dyn2DDRRSeqList = createDRRDynamic2DSequences(dynSeq, anglesAndAxisList)
    print(len(dyn2DDRRSeqList))
    print(type(dyn2DDRRSeqList[0]))

    for dyn2DSeq in dyn2DDRRSeqList:
        print(type(dyn2DSeq))
        print(len(dyn2DSeq.dyn2DImageList))
        print(type(dyn2DSeq.dyn2DImageList[0]))

    plt.figure()
    plt.imshow(dyn2DDRRSeqList[0].dyn2DImageList[0].imageArray)
    plt.show()

    print('!!!!!!!!!!!!!!!!!!!!createDRRDynamic2DSequences example end!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    if dynSeq.patient != None:
        for dyn2DSeq in dyn2DDRRSeqList:
            dynSeq.patient.appendDyn2DSeq(dyn2DSeq)

    patient = Patient()
    patient.name = 'testPatient'
    # Add the model and rtStruct to the patient
    patient.appendPatientData(dynSeq)
    for dyn2DSeq in dyn2DDRRSeqList:
        patient.appendPatientData(dyn2DSeq)

    # save resulting dynamic2DSequences with 3D dynamic sequence in drive
    savingPath = 'C:/Users/damie/Desktop/' + 'dyn2DDRRSeqList'
    saveSerializedObjects(patient, savingPath)
