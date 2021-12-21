
import logging
import numpy as np

from Controllers.modelController import ModelController
from Core.Data.patient import Patient
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.rtStruct import RTStruct
from Core.IO import dataLoader
from Controllers.DataControllers.image3DController import Image3DController
from Controllers.DataControllers.ctImageController import CTImageController
from Controllers.DataControllers.doseImageController import DoseImageController
from Controllers.DataControllers.patientController import PatientController
from Controllers.DataControllers.rtStructController import RTStructController
from Controllers.api import API

class DataLoaderController(ModelController):
    def __init__(self, patientListController):
        ModelController.__init__(self, patientListController)

        API.registerToAPI(self.loadData.__name__, self.loadData)
        API.registerToAPI(self.loadDummyImages.__name__, self.loadDummyImages)


    def loadData(self, dataPath, maxDepth=-1, ignoreExistingData=True, importInPatient=None):
        #TODO: implement ignoreExistingData

        dataList = dataLoader.loadAllData(dataPath, maxDepth=maxDepth)

        if importInPatient != None:
            index = self.patientListController.getIndex(importInPatient)
            patientController = self.patientListController.getPatientController(index)

        for data in dataList:
            if importInPatient == None:
                # check if patient already exists
                index = self.patientListController.getIndexFromPatientID(data.patientInfo.patientID)
                if index < 0:
                    index = self.patientListController.getIndexFromPatientName(data.patientInfo.name)

                # create new patient if not found in PatientList
                if index < 0:
                    patientController = PatientController(Patient(patientInfo = data.patientInfo))
                    self.patientListController.append(patientController)
                    index = len(self.patientListController) - 1

                patientController = self.patientListController.getPatientController(index)

            # add data to patient
            if(isinstance(data, Image3D)):
                imageController = Image3DController(data)
                patientController.appendImage(imageController)
            elif(isinstance(data, CTImage)):
                imageController = CTImageController(data)
                patientController.appendImage(imageController)
            elif(isinstance(data, DoseImage)):
                imageController = DoseImageController(data)
                patientController.appendImage(imageController)
            elif(isinstance(data, RTStruct)):
                structController = RTStructController(data)
                patientController.appendRTStruct(structController)
            else:
                logging.warning("WARNING: " + str(data.__class__) + " not loadable yet")
                continue

    def loadDummyImages(self, dataPath):
        #image = DICOMReader.read(dataPath)
        #image = Image3D(data=np.random.randint(2000, size=(100, 100, 100)), origin=(10, 20, 30), spacing=(1, 1, 1))
        data = np.zeros((100, 100, 100))+100
        data[10:20, 20:30, :] = 500

        data[2:5, 2:5, :] = 500
        image = Image3D(data=data, origin=(0, 0, 0), spacing=(1, 1, 1))
        imageController = Image3DController(image)
        imageController.setName('image' + str(len(self.patientListController.data)))

        image2 = Image3D(data=np.random.randint(2000, size=(100, 100, 100)), origin=(0, 0, 0), spacing=(1, 1, 1))
        imageController2 = Image3DController(image2)
        imageController2.setName('image' + str(len(self.patientListController.data)) + '_2')


        patientController = PatientController(Patient())
        patientController.setName('Patient' + str(len(self.patientListController.data)))
        self.patientListController.append(patientController)
        patientController.appendImage(imageController)
        patientController.appendImage(imageController2)