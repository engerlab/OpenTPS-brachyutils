from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController


class Image3DController(DataController):
    nameChangedSignal = pyqtSignal(str)
    dataChangedSignal = pyqtSignal(object)

    def __init__(self, image):
        super().__init__(image)

        if hasattr(self, '_uniqueImage3DControllerProperty'):
            return

        self._uniqueImage3DControllerProperty = True

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

    def getName(self):
        return self.data.name

    def setName(self, name):
        self.data.name = name
        self.nameChangedSignal.emit(self.data.name)

    def notifyDataChange(self):
        self.dataChangedSignal.emit(self.data)
