from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController
from Controllers.DataControllers.image3DController import Image3DController
from Controllers.DataControllers.rtStructController import RTStructController


class PatientController(DataController):
    imageAddedSignal = pyqtSignal(object)
    imageRemovedSignal = pyqtSignal(object)
    rtStructAddedSignal = pyqtSignal(object)
    rtStructRemovedSignal = pyqtSignal(object)
    nameChangedSignal = pyqtSignal(str)

    def __init__(self, patient):
        super().__init__(patient)

    def appendImage(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        self.data.appendImage(image)
        self.imageAddedSignal.emit(Image3DController(image))

    def appendRTStruct(self, struct):
        if isinstance(struct, RTStructController):
            struct = struct.data

        self.data.appendRTStruct(struct)
        self.rtStructAddedSignal.emit(RTStructController(struct))

    def getName(self):
        return self.data.patientInfo.name

    def getImageControllers(self):
        return [Image3DController(image) for image in self.data.images]

    def getRTStructControllers(self):
        return [RTStructController(struct) for struct in self.data.rtStructs]

    def hasImage(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        return self.data.hasImage(image)

    def removeImage(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        self.data.removeImage(image)
        self.imageRemovedSignal.emit(Image3DController(image))

    def removeRTStruct(self, struct):
        if isinstance(struct, RTStructController):
            struct = struct.data

        self.data.removeRTStruct(struct)
        self.rtStructRemovedSignal.emit(RTStructController(struct))

    def setName(self, name):
        self.data.patientInfo.name = name

    def getImageIndex(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        self.data.list.index(image)