from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController


class RTStructController(DataController):
    nameChangedSignal = pyqtSignal(str)
    dataChangedSignal = pyqtSignal(object)

    def __init__(self, struct):
        super().__init__(struct)

    def getName(self):
        return self.data.name

    def setName(self, name):
        self.data.name = name
        self.nameChangedSignal.emit(self.data.name)

    def notifyDataChange(self):
        self.dataChangedSignal.emit(self.data)