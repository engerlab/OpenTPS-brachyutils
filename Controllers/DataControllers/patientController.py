from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController


class PatientController(DataController):
    imageAdded = pyqtSignal(object)
    imageRemoved = pyqtSignal(object)

    def __init__(self, patient):
        super().__init__(patient)

    def appendImage(self, image):
        self.data.appendImage(image)
        self.imageAdded.emit(image)

    def removeImage(self, image):
        self.data.removeImage(image)
        self.imageRemoved.emit(image)