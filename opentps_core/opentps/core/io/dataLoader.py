import os
from typing import Sequence

import pydicom
import logging

from opentps.core.data._patientData import PatientData
from opentps.core.data._patient import Patient
from opentps.core.data._patientList import PatientList
from opentps.core.io.dicomIO import readDicomCT, readDicomDose, readDicomVectorField, readDicomStruct, readDicomPlan
from opentps.core.io import mhdIO
from opentps.core.io.serializedObjectIO import loadDataStructure

def loadData(patientList: PatientList, dataPath, maxDepth=-1, ignoreExistingData=True, importInPatient=None):
    #TODO: implement ignoreExistingData

    dataList = readData(dataPath, maxDepth=maxDepth)

    patient = None

    if not (importInPatient is None):
        patient = importInPatient

    for data in dataList:
        if (isinstance(data, Patient)):
            patient = data
            try:
                patient = patientList.getPatientByPatientId(patient.id)
            except:
                patientList.append(patient)

        elif importInPatient is None:
            # check if patient already exists
            try:
                patient = patientList.getPatientByPatientId(data.patient.id)
            except:
                pass

            # TODO: Get patient by name?

        if patient is None:

            if data.patient is None:
                data.patient = Patient(name='You Know Who')

            patient = data.patient

            patientList.append(patient)

        if patient is None:
            patient = Patient()
            patientList.append(patient)

        # add data to patient
        if(isinstance(data, PatientData)):
            patient.appendPatientData(data)
        # elif (isinstance(data, Dynamic2DSequence)): ## not implemented in patient yet, maybe only one function for both 2D and 3D dynamic sequences ?
        #     patient.appendDyn2DSeq(data)
        elif (isinstance(data, Patient)):
            pass  # see above, the Patient case is considered
        else:
            logging.warning("WARNING: " + str(data.__class__) + " not loadable yet")
            continue

def readData(inputPaths, maxDepth=-1) -> Sequence[PatientData]:
    """
    Load all data found at the given input path.

    Parameters
    ----------
    inputPaths: str or list
        Path or list of paths pointing to the data to be loaded.

    maxDepth: int, optional
        Maximum subfolder depth where the function will check for data to be loaded.
        Default is -1, which implies recursive search over infinite subfolder depth.

    Returns
    -------
    dataList: list of data objects
        The function returns a list of data objects containing the imported data.

    """

    fileLists = listAllFiles(inputPaths, maxDepth=maxDepth)
    dataList = []

    # read Dicom files
    dicomCT = {}
    for filePath in fileLists["Dicom"]:
        dcm = pydicom.dcmread(filePath)

        # Dicom field
        if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.66.3" or dcm.Modality == "REG":
            field = readDicomVectorField(filePath)
            dataList.append(field)

        # Dicom CT
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.2":
            # Dicom CT are not loaded directly. All slices must first be classified according to SeriesInstanceUID.
            newCT = 1
            for key in dicomCT:
                if key == dcm.SeriesInstanceUID:
                    dicomCT[dcm.SeriesInstanceUID].append(filePath)
                    newCT = 0
            if newCT == 1:
                dicomCT[dcm.SeriesInstanceUID] = [filePath]

        # Dicom dose
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.2":
            dose = readDicomDose(filePath)
            dataList.append(dose)

        # Dicom RT plan
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.5":
            logging.warning("WARNING: cannot import ", filePath, " because photon RT plan is not implemented yet")

        # Dicom RT Ion plan
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.8":
            plan = readDicomPlan(filePath)
            dataList.append(plan)

        # Dicom struct
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.3":
            struct = readDicomStruct(filePath)
            dataList.append(struct)

        else:
            logging.warning("WARNING: Unknown SOPClassUID " + dcm.SOPClassUID + " for file " + filePath)

    # import Dicom CT images
    for key in dicomCT:
        ct = readDicomCT(dicomCT[key])
        dataList.append(ct)

    # read MHD images
    for filePath in fileLists["MHD"]:
        mhdImage = mhdIO.importImageMHD(filePath)
        dataList.append(mhdImage)

    # read serialized object files
    for filePath in fileLists["Serialized"]:
        dataList += loadDataStructure(filePath) # not append because loadDataStructure returns a list already
        print('---------', type(dataList[-1]))

    return dataList


def readSingleData(filePath, dicomCT = {}):
    if os.path.isdir(filePath):
        # Check that it is a DICOM CT otherwise error
        listFiles = listAllFiles(filePath, maxDepth=0)
        if len(listFiles['Serialized'])>0 or len(listFiles['MHD'])>0:
            logging.error('readSingleData should not contain multiple files')
            return
        for file_i in listFiles["Dicom"]:
            readSingleData(file_i, dicomCT)
        if len(dicomCT)==0:
            logging.error('readSingleData should not contain multiple files')
            return
        # import Dicom CT images
        if len(dicomCT)>1:
            logging.error('readSingleData should not contain multiple CT.')
            return
        ctFile = list(dicomCT.values())[0]
        ct = readDicomCT(ctFile)
        return ct
    else:
        filetype = get_file_type(filePath)
        if filetype == 'Dicom':
            dcm = pydicom.dcmread(filePath)

            # Dicom field
            if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.66.3" or dcm.Modality == "REG":
                field = readDicomVectorField(filePath)
                return field

            # Dicom CT
            elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.2":
                # Dicom CT are not loaded directly. All slices must first be classified according to SeriesInstanceUID.
                newCT = 1
                for key in dicomCT:
                    if key == dcm.SeriesInstanceUID:
                        dicomCT[dcm.SeriesInstanceUID].append(filePath)
                        newCT = 0
                if newCT == 1:
                    dicomCT[dcm.SeriesInstanceUID] = [filePath]
                

            # Dicom dose
            elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.2":
                dose = readDicomDose(filePath)
                return dose

            # Dicom RT plan
            elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.5":
                logging.warning("WARNING: cannot import ", filePath, " because photon RT plan is not implemented yet")

            # Dicom RT Ion plan
            elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.8":
                plan = readDicomPlan(filePath)
                return plan

            # Dicom struct
            elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.3":
                struct = readDicomStruct(filePath)
                return struct

            else:
                logging.warning("WARNING: Unknown SOPClassUID " + dcm.SOPClassUID + " for file " + filePath)

        # read MHD image
        if filetype == "MHD":
            mhdImage = mhdIO.importImageMHD(filePath)
            return mhdImage

        # read serialized object files
        if filetype == "Serialized":
            return loadDataStructure(filePath)
        
        if filetype is None:
            return None


def get_file_type(filePath):
    # Is Dicom file ?
    dcm = None
    try:
        dcm = pydicom.dcmread(filePath)
    except:
        pass
    if(dcm != None):
        return 'Dicom'

    # Is MHD file ?
    with open(filePath, 'rb') as fid:
        data = fid.read(50*1024)  # read 50 kB, which should be more than enough for MHD header
        if data.isascii():
            if("ElementDataFile" in data.decode('ascii')): # recognize key from MHD header
                return 'MHD'

    # Is serialized file ?
    if filePath.endswith('.p') or filePath.endswith('.pbz2') or filePath.endswith('.pkl') or filePath.endswith('.pickle'):
        return "Serialized"

    logging.info("INFO: cannot recognize file format of " + filePath)
    return None



def listAllFiles(inputPaths, maxDepth=-1):
    """
    List all files of compatible data format from given input paths.

    Parameters
    ----------
    inputPaths: str or list
        Path or list of paths pointing to the data to be listed.

    maxDepth: int, optional
        Maximum subfolder depth where the function will check for files to be listed.
        Default is -1, which implies recursive search over infinite subfolder depth.

    Returns
    -------
    fileLists: dictionary
        The function returns a dictionary containing lists of data files classified according to their file format (Dicom, MHD).

    """

    fileLists = {
        "Dicom": [],
        "MHD": [],
        "Serialized": []
    }

    # if inputPaths is a list of path, then iteratively call this function with each path of the list
    if(isinstance(inputPaths, list)):
        for path in inputPaths:
            lists = listAllFiles(path, maxDepth=maxDepth)
            for key in fileLists:
                fileLists[key] += lists[key]

        return fileLists


    # check content of the input path
    if os.path.isdir(inputPaths):
        inputPathContent = sorted(os.listdir(inputPaths))
    else:
        inputPathContent = [inputPaths]
        inputPaths = ""


    for fileName in inputPathContent:
        filePath = os.path.join(inputPaths, fileName)

        # folders
        if os.path.isdir(filePath):
            if(maxDepth != 0):
                subfolderFileList = listAllFiles(filePath, maxDepth=maxDepth-1)
                for key in fileLists:
                    fileLists[key] += subfolderFileList[key]

        # files
        elif os.path.isfile(filePath):
            filetype = get_file_type(filePath)
            if filetype is None:
                logging.info("INFO: cannot recognize file format of " + filePath)
            else:
                fileLists[filetype].append(filePath)

    return fileLists



