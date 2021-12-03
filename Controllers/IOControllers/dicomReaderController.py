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
        image = Image3D(data=np.zeros((100, 100, 100)), origin=(0, 0, 0), spacing=(1, 1, 1))
        imageController = Image3DController(image)
        imageController.setName('image' + str(len(self.patientListController.data)))
        patientController = PatientController(Patient())
        patientController.setName('Patient' + str(len(self.patientListController.data)))
        self.patientListController.append(patientController)
        patientController.appendImage(imageController)

        print(image)
