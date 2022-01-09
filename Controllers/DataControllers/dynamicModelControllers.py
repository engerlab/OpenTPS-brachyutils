from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController
from Controllers.DataControllers.image3DController import Image3DController
from Controllers.DataControllers.vectorField3DController import VectorField3DController

class Dynamic3DModelController(DataController):
    nameChangedSignal = pyqtSignal(str)
    dataChangedSignal = pyqtSignal(object)

    def __init__(self, dynamic3DModel):
        super().__init__(dynamic3DModel)

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

    def getImageController(self):
        return Image3DController(self.data.midp)

    def getVectorFieldControllers(self):
        return [VectorField3DController(vectorField) for vectorField in self.data.deformationList]

