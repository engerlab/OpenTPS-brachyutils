import os
from pathlib import Path
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)

import opentps
from Core.IO.dataLoader import readData
from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.Data._patient import Patient
from Core.Processing.ImageSimulation.DRRToolBox import createDRRDynamic2DSequences
from Core.IO.serializedObjectIO import saveSerializedObjects, dictionarizeData
import matplotlib.pyplot as plt

from Core.Data.Images._ctImage import CTImage

if __name__ == '__main__':

    # Get the current working directory, its parent, then add the testData folder at the end of it
    testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')
    dataPath = testDataPath + "4DCTDicomLight/00"
    print(dataPath)
    dataList = readData(dataPath)

    for element in dataList:
        print(type(element))

    # dataDict = dictionarizeData(dataList[0])
    #
    # print(dataDict.keys())
    # print(dataDict['dataType'])

    dataPath = "D:/testSavedDictList"
    saveSerializedObjects(dataList[0], dataPath)

    dataPath = "D:/testSavedDictList.p"
    dataList = readData(dataPath)

    patient = Patient()
    for element in dataList:
        patient.appendPatientData(element)

    patient.name = 'Mystery'

    patientList = opentps.patientList
    patientList.append(patient)

    opentps.run()

    #
    # # print(type(dataList[0]))
    # #
    # print(dataList[0].name)
    # print(dataList[0].origin)
    # print(dataList[0].spacing)
    # print(dataList[0].name)
    #
    # plt.figure()
    # plt.imshow(dataList[0].imageArray[:,:,100])
    # plt.show()