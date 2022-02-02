
import logging

from Core.Data.patient import Patient
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.vectorField3D import VectorField3D
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.Data.dynamic3DModel import Dynamic3DModel
from Core.Data.dynamic2DSequence import Dynamic2DSequence
from Core.Data.patientList import PatientList
from Core.Data.rtStruct import RTStruct
from Core.IO import dataLoader
from API.api import API


@API.apiMethod
def loadData(patientList: PatientList, dataPath, maxDepth=-1, ignoreExistingData=True, importInPatient=None):
    #TODO: implement ignoreExistingData

    dataList = dataLoader.loadAllData(dataPath, maxDepth=maxDepth)

    patient = None

    if not (importInPatient is None):
        patient = importInPatient

    for data in dataList:
        if (isinstance(data, Patient)):
            patient = data
            patientList.append(patient)

        if importInPatient is None:
            # check if patient already exists
            patient = patientList.getPatientByPatientId(data.patientInfo.patientID)

            # TODO: Get patient by name?

        if patient is None:
            patient = Patient(patientInfo = data.patientInfo)
            patientList.append(patient)

        # add data to patient
        if(isinstance(data, Image3D)):
            patient.appendImage(data)
        elif(isinstance(data, CTImage)):
            patient.appendImage(data)
        elif(isinstance(data, DoseImage)):
            patient.appendImage(data)
        elif(isinstance(data, RTStruct)):
            patient.appendRTStruct(data)
        elif (isinstance(data, VectorField3D)):
            patient.appendRTStruct(data)
        elif (isinstance(data, Dynamic3DSequence)):
            patient.appendDyn3DSeq(data)
        # elif (isinstance(data, Dynamic2DSequence)): ## not implemented in patient yet, maybe only one function for both 2D and 3D dynamic sequences ?
        #     patient.appendDyn2DSeq(data)
        elif (isinstance(data, Dynamic3DModel)):
            patient.appendDyn3DMod(data)
        elif (isinstance(data, Patient)):
            pass  # see above, the Patient case is considered
        else:
            logging.warning("WARNING: " + str(data.__class__) + " not loadable yet")
            continue
