
from Controllers.modelController import ModelController
from Core.IO import dataLoader

class DataLoaderController(ModelController):
    def __init__(self, patientList):
        super().__init__(self, patientList)

        self.apiMethods.loadData = self.loadData


    def loadData(self, dataPath):
        dataList = dataLoader.loadAllData(dataPath)