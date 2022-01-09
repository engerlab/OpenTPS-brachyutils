from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController
from Controllers.DataControllers.image3DController import Image3DController

class Dynamic3DSequenceController(DataController):
    nameChangedSignal = pyqtSignal(str)
    dataChangedSignal = pyqtSignal(object)

    def __init__(self, dynamic3DSequence):
        super().__init__(dynamic3DSequence)

    def getName(self):
        return self.data.name

    def setName(self, name):
        self.data.name = name
        self.nameChangedSignal.emit(self.data.name)

    def notifyDataChange(self):
        self.dataChangedSignal.emit(self.data)

    # def appendImage(self, image):
    #     if isinstance(image, Image3DController):
    #         image = image.data
    #
    #     self.data.dyn3DImageList.appendImage(image)
    #     self.imageAddedSignal.emit(Image3DController(image))

    def getImageControllers(self):
        return [Image3DController(image) for image in self.data.dyn3DImageList]
