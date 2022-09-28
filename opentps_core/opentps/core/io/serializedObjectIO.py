"""
Made by damien (damien.dasnoy@uclouvain.be / damien.dasnoy@gmail.com)
"""
import bz2
import _pickle as cPickle
import pickle
import os

import matplotlib.pyplot as plt

from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.dynamicData.dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData.dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._vectorField3D import VectorField3D
from opentps.core.data._patient import Patient

# ---------------------------------------------------------------------------------------------------



def saveDataStructure(patientList, savingPath, compressedBool=False, splitPatientsBool=False):
    if splitPatientsBool:
        patientList = [[patient] for patient in patientList]
        for patient in patientList:
            patientName = '_' + patient[0].name
            saveSerializedObjects(patient, savingPath + patientName, compressedBool=compressedBool)

    else:
        saveSerializedObjects(patientList, savingPath, compressedBool=compressedBool)


# ---------------------------------------------------------------------------------------------------
def saveSerializedObjects(dataList, savingPath, compressedBool=False, dictionarized=False):


    if type(dataList) != list:
        dataList = [dataList]

    if dictionarized:
        for elementIdx in range(len(dataList)):
            dataList[elementIdx] = dictionarizeData(dataList[elementIdx])

    if compressedBool:
        print('Compress and save serialized data structure in drive')
        with bz2.BZ2File(savingPath + '_compressed.pbz2', 'w') as f:
            cPickle.dump(dataList, f)

    else:
        print('Save serialized data structure in drive')
        # basic version
        # pickle.dump(self.Patients, open(savingPath + ".p", "wb"), protocol=4)

        # large file version
        max_bytes = 2 ** 31 - 1
        bytes_out = pickle.dumps(dataList)
        with open(savingPath + ".p", 'wb') as f_out:
            for idx in range(0, len(bytes_out), max_bytes):
                f_out.write(bytes_out[idx:idx + max_bytes])

    print('Serialized data structure saved in drive:', savingPath + ".p")



# ---------------------------------------------------------------------------------------------------
def loadDataStructure(filePath):
    if filePath.endswith('.p') or filePath.endswith('.pkl') or filePath.endswith('.pickle'):
        # option using basic pickle function
        # self.Patients.list.append(pickle.load(open(dictFilePath, "rb")).list[0])

        # option for large files
        max_bytes = 2 ** 31 - 1
        bytes_in = bytearray(0)
        input_size = os.path.getsize(filePath)
        with open(filePath, 'rb') as f_in:
            for _ in range(0, input_size, max_bytes):
                bytes_in += f_in.read(max_bytes)

        try:
            dataList = pickle.loads(bytes_in)
        except:
            from opentps.core.utils import pickel2 as pickle2
            dataList = pickle2.loads(bytes_in)

    elif filePath.endswith('.pbz2'):
        dataList = bz2.BZ2File(filePath, 'rb')
        dataList = cPickle.load(dataList)

    print('Serialized data list of', len(dataList), 'items loaded')
    for itemIndex, item in enumerate(dataList):
        if type(item) == dict:
            dataList[itemIndex] = unDictionarize(dataList[itemIndex])
        print(itemIndex + 1, type(item))

    return dataList


# ---------------------------------------------------------------------------------------------------
def loadSerializedObject(filePath):
    """
    to do in the same way as for saving (object - structure)
    """
    pass



def saveRTPlan(plan, file_path):
    if plan.planDesign.beamlets:
        plan.planDesign.beamlets.unload()
    if plan.planDesign.beamletsLET:
        plan.planDesign.beamletsLET.unload()

    for scenario in plan.planDesign.scenarios:
        scenario.unload()

    with open(file_path, 'wb') as fid:
        pickle.dump(plan.__dict__, fid)


def loadRTPlan(file_path):
    with open(file_path, 'rb') as fid:
        tmp = pickle.load(fid)

    plan = RTPlan()
    plan.__dict__.update(tmp)
    return plan


def saveBeamlets(beamlets, file_path):
    beamlets.storeOnFS(file_path)

def loadBeamlets(file_path):
    from opentps.core.data._sparseBeamlets import SparseBeamlets
    return loadData(file_path, SparseBeamlets)

def saveData(data, file_path):
    with open(file_path, 'wb') as fid:
        pickle.dump(data.__dict__, fid, protocol=4)

def loadData(file_path, cls):
    with open(file_path, 'rb') as fid:
        tmp = pickle.load(fid)
    data = cls()
    data.__dict__.update(tmp)
    return data


def dictionarizeData(data):

    print('Dictionarize data -', data.getTypeAsString())
    newDict = {}

    if isinstance(data, Patient):

        patientDataDictList = []
        for patientData in data.patientData:
            patientDataDictList.append(dictionarizeData(patientData))

        data.patientData = None
        patient = dictionarizeData(data)

        print(patient.keys())

    elif isinstance(data, Dynamic3DModel):

        newDict = data.__dict__

        midPDict = dictionarizeData(data.midp)
        newDict['midp'] = midPDict

        defDictList = []
        for field in data.deformationList:
            defDictList.append(dictionarizeData(field))

        newDict['deformationList'] = defDictList

        newDict['dataType'] = data.getTypeAsString()

    elif isinstance(data, Dynamic3DSequence):

        newDict = data.__dict__
        dynImagesDictList = []
        for img in data.dyn3DImageList:
            dynImagesDictList.append(dictionarizeData(img))

        newDict['dyn3DImageList'] = dynImagesDictList
        newDict['dataType'] = data.getTypeAsString()

    elif isinstance(data, CTImage):

        newDict = data.__dict__
        newDict['dataType'] = data.getTypeAsString()

    elif isinstance(data, VectorField3D):

        newDict = data.__dict__
        newDict['dataType'] = data.getTypeAsString()

    else:
        newDict = data.__dict__
        newDict['dataType'] = data.getTypeAsString()

    print(newDict.keys())

    return newDict

def unDictionarize(dataDict):

    print('Read data under dict Format -', dataDict['dataType'])
    data = None

    print(dataDict.keys())

    if dataDict['dataType'] == 'Dynamic3DModel':
        data = Dynamic3DModel()

        patient = dataDict['patient']
        dataDict['patient'] = None
        data.__dict__.update(dataDict)
        data.patient = patient

        # data.__dict__.update(dataDict)
        data.midp = unDictionarize(dataDict['midp'])

        for field in dataDict['deformationList']:
            data.deformationList.append(unDictionarize(field))

    elif dataDict['dataType'] == 'Dynamic3DSequence':
        data = Dynamic3DSequence()
        data.__dict__.update(dataDict)

        for img in dataDict['dyn3DImageList']:
            data.dyn3DImageList.append(unDictionarize(img))

    elif dataDict['dataType'] == 'CTImage':

        print('--------------------')
        print(dataDict.keys())
        data = CTImage()
        print(data.__dict__)
        data.__dict__.update(dataDict)
        print(data.__dict__)

        print('in serializedIO, unDict')
        plt.figure()
        plt.imshow(data.imageArray[:,:,20])
        plt.show()

    elif dataDict['dataType'] == 'VectorField3D':
        data = VectorField3D()
        data.__dict__.update(dataDict)

    else:
        NotImplementedError

    return data


