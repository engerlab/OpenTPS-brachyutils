from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController
from Controllers.DataControllers.image3DController import Image3DController


class PatientController(DataController):
    imageAdded = pyqtSignal(object)
    imageRemoved = pyqtSignal(object)
    nameChanged = pyqtSignal(str)

    def __init__(self, patient):
        super().__init__(patient)

    def appendImage(self, image):
        self.data.appendImage(image)
        self.imageAdded.emit(image)

    def getName(self):
        return self.data.name

    def getImageControllers(self):
        return [Image3DController(image) for image in self.data.images]

    def removeImage(self, image):
        self.data.removeImage(image)
        self.imageRemoved.emit(image)

    def setName(self, name):
        self.data.name = name