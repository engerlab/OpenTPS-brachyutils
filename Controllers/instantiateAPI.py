from Controllers.IOControllers.dicomReaderController import DICOMReaderController
from Controllers.modelController import ModelController


def instantiateAPI(patientListController):
    DICOMReaderController(patientListController)