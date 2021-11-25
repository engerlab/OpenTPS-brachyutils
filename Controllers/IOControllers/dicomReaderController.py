from PyQt5.QtCore import QObject

from Controllers.modelController import ModelController
from Core.IO.dicomReader import DICOMReader


class DICOMReaderController(ModelController):

    def __init__(self):
        QObject.__init__(self)

        self.apiMethods.DICOMReadImage = self.loadImage

    #TODO: This is just for the refactoring workshop. We should do smthg much better
    def loadImage(self, dataPath):
        image = DICOMReader.read(dataPath)
