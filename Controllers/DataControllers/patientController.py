from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController
from Controllers.DataControllers.image3DController import Image3DController
from Controllers.DataControllers.rtStructController import RTStructController
from Controllers.DataControllers.dynamicSequenceControllers import Dynamic3DSequenceController
from Controllers.DataControllers.dynamicModelControllers import Dynamic3DModelController


class PatientController(DataController):
    imageAddedSignal = pyqtSignal(object)
    imageRemovedSignal = pyqtSignal(object)
    rtStructAddedSignal = pyqtSignal(object)
    rtStructRemovedSignal = pyqtSignal(object)
    dyn3DSeqAddedSignal = pyqtSignal(object)
    dyn3DSeqRemovedSignal = pyqtSignal(object)
    dyn3DModAddedSignal = pyqtSignal(object)
    dyn3DModRemovedSignal = pyqtSignal(object)
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
        if isinstance(dyn3DSeq, Dynamic3DSequenceController):
            dyn3DSeq = dyn3DSeq.data

        self.data.appendDyn3DSeq(dyn3DSeq)
        self.dyn3DSeqAddedSignal.emit(Dynamic3DSequenceController(dyn3DSeq))

    def appendDyn3DMod(self, dyn3DMod):
        if isinstance(dyn3DMod, Dynamic3DModelController):
            dyn3DMod = dyn3DMod.data

        self.data.appendDyn3DMod(dyn3DMod)
        self.dyn3DModAddedSignal.emit(Dynamic3DModelController(dyn3DMod))

    def getName(self):
        return self.data.patientInfo.name

    def getImageControllers(self):
        return [Image3DController(image) for image in self.data.images]

    def getRTStructControllers(self):
        return [RTStructController(struct) for struct in self.data.rtStructs]

    def getDynamic3DSequenceControllers(self):
        return [Dynamic3DSequenceController(dynSeq) for dynSeq in self.data.dynamic3DSequences]

    def getDynamic3DModelControllers(self):
        return [Dynamic3DModelController(dynMod) for dynMod in self.data.dynamic3DModels]

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
        if isinstance(dyn3DSeq, Dynamic3DSequenceController):
            dyn3DSeq = dyn3DSeq.data

        self.data.removeDyn3DSeq(dyn3DSeq)
        self.dyn3DSeqRemovedSignal.emit(Dynamic3DSequenceController(dyn3DSeq))

    def removeDyn3DMod(self, dyn3DMod):
        if isinstance(dyn3DMod, Dynamic3DModelController):
            dyn3DMod = dyn3DMod.data

        self.data.removeDyn3DMod(dyn3DMod)
        self.dyn3DModRemovedSignal.emit(Dynamic3DModelController(dyn3DMod))

    def setName(self, name):
        self.data.patientInfo.name = name

    def getImageIndex(self, image):
        if isinstance(image, Image3DController):
            image = image.data

        self.data.list.index(image)