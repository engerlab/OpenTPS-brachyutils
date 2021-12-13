
from Controllers.modelController import ModelController
from Controllers.api import API
from Core.IO import dataLoader

class DataLoaderController(API):
    def __init__(self, patientListController):
        super().__init__(self, patientListController)

        API.__init__(self, patientListController)
        self.registerToAPI(self.loadData.__name__, self.loadData)


    def loadData(self, dataPath):
        dataList = dataLoader.loadAllData(dataPath)