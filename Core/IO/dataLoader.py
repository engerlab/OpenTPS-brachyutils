import os
import pydicom
import logging

from Core.IO.dicomReader import readDicomCT, readDicomDose


def loadAllData(inputPaths, maxDepth=-1):
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

        # Dicom CT
        if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.2":
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

        # Dicom RT Plan
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.5":
            logging.warning("WARNING: cannot import ", file_path, " because photon RT plan is not implemented yet")

        # Dicom RT Ion Plan
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.8":
            logging.warning("WARNING: cannot import " + filePath + " because RT ion plan import is not implemented yet")

        # Dicom struct
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.3":
            logging.warning("WARNING: cannot import " + filePath + " because RT Struct import is not implemented yet")

        else:
            logging.warning("WARNING: Unknown SOPClassUID " + dcm.SOPClassUID + " for file " + filePath)

    # import Dicom CT images
    for key in dicomCT:
        ct = readDicomCT(dicomCT[key])
        dataList.append(ct)

    # read MHD images
    for filePath in fileLists["MHD"]:
        logging.warning("WARNING: cannot import " + filePath + " because MHD import is not implemented yet")


    return dataList



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
        "MHD": []
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
        inputPathContent = os.listdir(inputPaths)
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

            # Is Dicom file ?
            dcm = None
            try:
                dcm = pydicom.dcmread(filePath)
            except:
                pass
            if(dcm != None):
                fileLists["Dicom"].append(filePath)
                continue


            # Is MHD file ?
            with open(filePath, 'rb') as fid:
                data = fid.read(50*1024)  # read 50 kB, which should be more than enough for MHD header
                if data.isascii():
                    if("ElementDataFile" in data.decode('ascii')): # recognize key from MHD header
                        fileLists["MHD"].append(filePath)
                        continue

            # Unknown file format
            logging.info("INFO: cannot recognize file format of ", filePath)

    return fileLists



