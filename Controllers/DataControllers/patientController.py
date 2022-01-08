from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController
from Controllers.DataControllers.image3DController import Image3DController
from Controllers.DataControllers.rtStructController import RTStructController
from Controllers.DataControllers.dynamicSequenceController import DynamicSequenceController


class PatientController(DataController):
    imageAddedSignal = pyqtSignal(object)
    imageRemovedSignal = pyqtSignal(object)
    rtStructAddedSignal = pyqtSignal(object)
    rtStructRemovedSignal = pyqtSignal(object)
    dyn3DSeqAddedSignal = pyqtSignal(object)
    dyn3DSeqRemovedSignal = pyqtSignal(object)
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

    def appendDyn3DSeq(self, dyn3DSeq):
        if isinstance(dyn3DSeq, DynamicSequenceController):
            dyn3DSeq = dyn3DSeq.data

        self.data.appendDyn3DSeq(dyn3DSeq)
        self.dyn3DSeqAddedSignal.emit(DynamicSequenceController(dyn3DSeq))

    def getName(self):
        return self.data.patientInfo.name

    def getImageControllers(self):
        return [Image3DController(image) for image in self.data.images]

    def getRTStructControllers(self):
        return [RTStructController(struct) for struct in self.data.rtStructs]

    def getDynamic3DSequenceControllers(self):
        return [DynamicSequenceController(dynSeq) for dynSeq in self.data.dynamic3DSequences]

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

    def removeDyn3DSeq(self, dyn3DSeq):
        if isinstance(dyn3DSeq, DynamicSequenceController):
            dyn3DSeq = dyn3DSeq.data

        self.data.removeDyn3DSeq(dyn3DSeq)
        self.dyn3DSeqRemovedSignal.emit(DynamicSequenceController(dyn3DSeq))

    def setName(self, name):
        self.data.patientInfo.name = name

    def getImageIndex(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        self.data.list.index(image)