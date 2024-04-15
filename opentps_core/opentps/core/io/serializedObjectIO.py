"""
Made by damien (damien.dasnoy@uclouvain.be / damien.dasnoy@gmail.com)
"""
import bz2
import _pickle as cPickle
import pickle
import os
import logging
import matplotlib.pyplot as plt

from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData._dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._vectorField3D import VectorField3D
from opentps.core.data._patient import Patient



logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------------------------------
def saveDataStructure(patientList, savingPath, compressedBool=False, splitPatientsBool=False):
    """
    Save OpenTPS data structures of a list of patient in the hard drive

    Parameters
    ----------
    patientList : list
        List of patients to save
    savingPath : str
        Path where to save the data structure
    compressedBool : bool, optional
        If True, the data structure is compressed before saving. The default is False.
    splitPatientsBool : bool, optional
        If True, each patient is saved in a separate file. The default is False.
    """
    if splitPatientsBool:
        patientList = [[patient] for patient in patientList]
        for patient in patientList:
            patientName = '_' + patient[0].name
            saveSerializedObjects(patient, savingPath + patientName, compressedBool=compressedBool)

    else:
        saveSerializedObjects(patientList, savingPath, compressedBool=compressedBool)


# ---------------------------------------------------------------------------------------------------
def saveSerializedObjects(dataList, savingPath, compressedBool=False, dictionarized=False):

    """
    Save a list of OpenTPS objects in the hard drive

    Parameters
    ----------
    dataList : list
        List of OpenTPS objects to save
    savingPath : str
        Path where to save the data structures
    compressedBool : bool, optional
        If True, the data structure is compressed before saving. The default is False.
    dictionarized : bool, optional
        If True, the data structure is dictionarized before saving to avoid loss
         of information over long-term storage due to class objects modifications.
         The default is False.
    """

    if type(dataList) != list:
        dataList = [dataList]
        # print("datalist", dataList)
    if dictionarized:
        for elementIdx in range(len(dataList)):
            dataList[elementIdx] = dictionarizeData(dataList[elementIdx])
    
    if compressedBool:
        logger.info(f'Compressed Serialized data structure saved in drive: {savingPath} .p')
        with bz2.BZ2File(savingPath + '_compressed.pbz2', 'w') as f:
            cPickle.dump(dataList, f)

    else:
        logger.info(f'Serialized data structure saved in drive: {savingPath} .p')
        # basic version
        # pickle.dump(self.Patients, open(savingPath + ".p", "wb"), protocol=4)

        # large file version
        max_bytes = 2 ** 31 - 1
        bytes_out = pickle.dumps(dataList)
        with open(savingPath + ".p", 'wb') as f_out:
            for idx in range(0, len(bytes_out), max_bytes):
                f_out.write(bytes_out[idx:idx + max_bytes])


# ---------------------------------------------------------------------------------------------------
def loadDataStructure(filePath):

    """
    Load a OpenTPS data structure from the hard drive

    Parameters
    ----------
    filePath : str
        Path where to load the data structure

    Returns
    -------
    dataList : list
        List of OpenTPS objects loaded.
    """

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

    logger.info(f'Serialized data list of {len(dataList)} items loaded')
    for itemIndex, item in enumerate(dataList):
        if type(item) == dict:
            dataList[itemIndex] = unDictionarize(dataList[itemIndex])
        else:
            dataList[itemIndex] = copyIntoNewObject(dataList[itemIndex])
        logger.info(f'{itemIndex + 1}, {type(item)}')

    return dataList


# ---------------------------------------------------------------------------------------------------
def loadSerializedObject(filePath):
    """
    TODO
    to do in the same way as for saving (object - structure)
    """
    print('loadSerializedObject not implemented yet')

    pass



def saveRTPlan(plan, file_path):
    """
    Save the RTPlan object in a file

    Parameters
    ----------
    plan : RTPlan
        The RTPlan object to save
    file_path : str
        The path of the file where to save the RTPlan object
    """
    if plan.planDesign:
        if plan.planDesign.beamlets:
            plan.planDesign.beamlets.unload()
        if plan.planDesign.beamletsLET:
            plan.planDesign.beamletsLET.unload()

        for scenario in plan.planDesign.robustness.scenarios:
            scenario.unload()

    with open(file_path, 'wb') as fid:
        pickle.dump(plan.__dict__, fid)


def loadRTPlan(file_path):
    """
    Load a RTPlan object from a file

    Parameters
    ----------
    file_path : str
        The path of the file to load the RTPlan

    Returns
    -------
    plan:RTPlan
        The RTPlan object loaded from the file
    """
    with open(file_path, 'rb') as fid:
        tmp = pickle.load(fid)

    plan = RTPlan()
    plan.__dict__.update(tmp)
    return plan


def saveBeamlets(beamlets, file_path):
    """
    Save the beamlets object in a file

    Parameters
    ----------
    beamlets : SparseBeamlets
        The beamlets object to save
    file_path : str
        The path of the file where to save the beamlets object
    """
    beamlets.storeOnFS(file_path)

def loadBeamlets(file_path):
    """
    Load a beamlets object from a file

    Parameters
    ----------
    file_path : str
        The path of the file to load the beamlets

    Returns
    -------
    beamlets:SparseBeamlets
        The beamlets object loaded from the file
    """
    from opentps.core.data._sparseBeamlets import SparseBeamlets
    return loadData(file_path, SparseBeamlets)

def saveData(data, file_path):
    """
    Save the data object in a file (pickle)

    Parameters
    ----------
    data : object
        The data object to save
    file_path : str
        The path of the file where to save the data object
    """
    with open(file_path, 'wb') as fid:
        pickle.dump(data.__dict__, fid, protocol=4)

def loadData(file_path, cls):
    """
    Load a data object from a file (pickle)

    Parameters
    ----------
    file_path : str
        The path of the file to load the data
    cls : class
        The class of the data object to load
    """
    with open(file_path, 'rb') as fid:
        tmp = pickle.load(fid)
    data = cls()
    data.__dict__.update(tmp)
    return data


def dictionarizeData(data):
    """
    Convert an OpenTPS object into a dictionary

    Parameters
    ----------
    data : object
        The OpenTPS object to convert

    Returns
    -------
    newDict : dict
        The dictionary containing the data of the OpenTPS object
    """

    print('Dictionarize data -', data.getTypeAsString())
    newDict = {}

    if isinstance(data, Patient):

        patientDataDictList = []
        for patientData in data.patientData:
            patientDataDictList.append(dictionarizeData(patientData))

        data.patientData = None
        patient = dictionarizeData(data)

        # print(patient.keys())

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

    # elif isinstance(data, CTImage):
    #
    #     newDict = data.__dict__
    #     newDict['dataType'] = data.getTypeAsString()

    elif isinstance(data, VectorField3D):

        newDict = data.__dict__
        newDict['dataType'] = data.getTypeAsString()

    else:
        print('in dictionarizeData else, data type: ', type(data))
        newDict = data.__dict__
        newDict['dataType'] = data.getTypeAsString()

    # print(newDict.keys())

    return newDict

def unDictionarize(dataDict):
    """
    Convert a dictionary into an OpenTPS object

    Parameters
    ----------
    dataDict : dict
        The dictionary containing the data of the OpenTPS object

    Returns
    -------
    data : object
        The OpenTPS object
    """

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

def copyIntoNewObject(sourceObject):
    """
    Copy the content of a source object into a new object of the same class

    Parameters
    ----------
    sourceObject : object
        The object to copy

    Returns
    -------
    newObject : object
        The new object with the same content as the source object
    """

    #print('in serializedObjectIO loadINtoNewObject')

    classOfSource = sourceObject.__class__
    newObject = classOfSource()

    for att, value in sourceObject.__dict__.items():
        setattr(newObject, att, value)

    return newObject