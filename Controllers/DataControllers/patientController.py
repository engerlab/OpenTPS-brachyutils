from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController
from Controllers.DataControllers.image3DController import Image3DController


class PatientController(DataController):
    imageAddedSignal = pyqtSignal(object)
    imageRemovedSignal = pyqtSignal(object)
    nameChangedSignal = pyqtSignal(str)

    def __init__(self, patient):
        super().__init__(patient)

    def appendImage(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        self.data.appendImage(image)
        self.imageAddedSignal.emit(Image3DController(image))

    def getName(self):
        return self.data.name

    def getImageControllers(self):
        return [Image3DController(image) for image in self.data.images]

    def hasImage(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        return self.data.hasImage(image)

    def removeImage(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        self.data.removeImage(image)
        self.imageRemovedSignal.emit(Image3DController(image))

    def setName(self, name):
        self.data.name = name

    def getImageIndex(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        self.data.list.index(image)