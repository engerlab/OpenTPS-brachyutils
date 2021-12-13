import pickle

import numpy as np
from PyQt5.QtCore import QObject

from Controllers.DataControllers.image3DController import Image3DController
from Controllers.DataControllers.patientController import PatientController
from Controllers.modelController import ModelController
from Core.Data.Images.image3D import Image3D
from Core.Data.patient import Patient
from Core.IO.dicomReader import DICOMReader


class DICOMReaderController(ModelController):
    def __init__(self, patientList):
        ModelController.__init__(self, patientList)

        self.apiMethods.readDicomImage = self.loadImage

    #TODO: This is just for the refactoring workshop. We should do smthg much better
    def loadImage(self, dataPath):
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
