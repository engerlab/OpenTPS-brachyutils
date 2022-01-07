from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController


class DynamicSequenceController(DataController):
    nameChangedSignal = pyqtSignal(str)
    dataChangedSignal = pyqtSignal(object)

    def __init__(self, dynamicSequence):
        super().__init__(dynamicSequence)

    def getName(self):
        return self.data.name

    def setName(self, name):
        self.data.name = name
        self.nameChangedSignal.emit(self.data.name)

    def notifyDataChange(self):
        self.dataChangedSignal.emit(self.data)
