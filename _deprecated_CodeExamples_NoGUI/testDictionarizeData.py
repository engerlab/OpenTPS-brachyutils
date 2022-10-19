import os
from pathlib import Path
import sys
import matplotlib.pyplot as plt
# currentWorkingDir = os.getcwd()
# sys.path.append(os.path.dirname(currentWorkingDir))

from opentps.core.io.dataLoader import readData
from opentps.core.data._patient import Patient
from opentps.core.io.serializedObjectIO import saveSerializedObjects


if __name__ == '__main__':

    # Get the current working directory, its parent, then add the testData folder at the end of it
    testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')
    dataPath = "D:/openTPSTestData"
    print(dataPath)
    dataList = readData(dataPath)

    for element in dataList:
        print(type(element))

    # dataDict = dictionarizeData(dataList[0])
    #
    # print(dataDict.keys())
    # print(dataDict['dataType'])

    dataPath = "D:/testSavedDictList"
    saveSerializedObjects(dataList, dataPath, dictionarized=True)

    dataPath = "D:/testSavedDictList.p"
    dataList = readData(dataPath)

    print(type(dataList[0]))

    # print(dataList[0].name)
    # print(dataList[0].origin)
    # print(dataList[0].spacing)
    # print(dataList[0].name)
    #
    # plt.figure()
    # plt.imshow(dataList[0].imageArray[:, :, 22])
    # plt.show()


    # create a patient, add the data and give him a name
    patient = Patient()
    for element in dataList:
        patient.appendPatientData(element)

    patient.name = 'Mystery'

    # launch the GUI with the patient we just filled already loaded
    import opentps.gui as GUI
    GUI.patientList.append(patient)
    GUI.run()

