
import logging

from Core.Data.patient import Patient
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.vectorField3D import VectorField3D
from Core.Data.rtStruct import RTStruct
from Core.IO import dataLoader
from Controllers.api import API

class DataLoaderController:
    def __init__(self, patientList):
        self._patientList = patientList

        API.registerToAPI(self.loadData.__name__, self.loadData)

    def loadData(self, dataPath, maxDepth=-1, ignoreExistingData=True, importInPatient=None):
        #TODO: implement ignoreExistingData

        dataList = dataLoader.loadAllData(dataPath, maxDepth=maxDepth)

        patient = None

        if not (importInPatient is None):
            patient = importInPatient

        for data in dataList:
            if (isinstance(data, Patient)):
                patient = data
                print('in dataLoaderController', patient.name)
                self._patientList.append(patient)

            if importInPatient is None:
                # check if patient already exists
                patient = self._patientList.getPatientByPatientId(data.patientInfo.patientID)

                # TODO: Get patient by name?

            if patient is None:
                patient = Patient(patientInfo = data.patientInfo)
                self._patientList.append(patient)

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
            elif (isinstance(data, Patient)):
                pass  # see above, the Patient case is considered
            else:
                logging.warning("WARNING: " + str(data.__class__) + " not loadable yet")
                continue
