
from Controllers.IOControllers.dicomReaderController import DICOMReaderController
from Controllers.IOControllers.dataLoaderController import DataLoaderController
from Controllers.api import API


def instantiateAPI(patientListController):
    DICOMReaderController(patientListController)
    DataLoaderController(patientListController)

    print('Methods instantiated:')
    print(API().getMethodsAsString())
