
from Controllers.modelController import ModelController
from Controllers.IOControllers.dicomReaderController import DICOMReaderController
from Controllers.IOControllers.dataLoaderController import DataLoaderController


def instantiateAPI(patientListController):
    DICOMReaderController(patientListController)
    DataLoaderController(patientListController)
