
from Controllers.IOControllers.dataLoaderController import DataLoaderController
from Controllers.api import API


def instantiateAPI(patientListController):
    DataLoaderController(patientListController)

    print('Methods instantiated:')
    print(API().getMethodsAsString())
