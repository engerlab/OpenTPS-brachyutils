from Controllers.IOControllers.dicomReaderController import DICOMReaderController
from Controllers.api import API


def instantiateAPI(patientListController):
    DICOMReaderController(patientListController)

    print('Methods instantiated:')
    print(API().getMethodsAsString())