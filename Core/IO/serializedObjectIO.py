"""
Made by damien (damien.dasnoy@uclouvain.be / damien.dasnoy@gmail.com)
"""
import bz2
import _pickle as cPickle
import pickle
import os


# ---------------------------------------------------------------------------------------------------
def saveDataStructure(patientList, savingPath, compressedBool=False, splitPatientsBool=False):

    if splitPatientsBool:
        patientList = [[patient] for patient in patientList]
        for patient in patientList:
            patientName = '_' + patient[0].patientInfo.name
            saveSerializedObject(patient, savingPath + patientName, compressedBool=compressedBool)

    else:
        saveSerializedObject(patientList, savingPath, compressedBool=compressedBool)


# ---------------------------------------------------------------------------------------------------
def saveSerializedObject(dataList, savingPath, compressedBool=False):

    if type(dataList) != list:
        dataList = [dataList]

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

    print('Serialized data structure saved in drive')


# ---------------------------------------------------------------------------------------------------
def loadDataStructure(filePath):

    if filePath.endswith('.p'):
        # option using basic pickle function
        # self.Patients.list.append(pickle.load(open(dictFilePath, "rb")).list[0])

        # option for large files
        max_bytes = 2 ** 31 - 1
        bytes_in = bytearray(0)
        input_size = os.path.getsize(filePath)
        with open(filePath, 'rb') as f_in:
            for _ in range(0, input_size, max_bytes):
                bytes_in += f_in.read(max_bytes)
        data = pickle.loads(bytes_in)

    elif filePath.endswith('.pbz2'):
        data = bz2.BZ2File(filePath, 'rb')
        data = cPickle.load(data)

    print('Serialized data list of', len(data), 'items loaded')
    for itemIndex, item in enumerate(data):
        print(itemIndex + 1, type(item))
    return data

