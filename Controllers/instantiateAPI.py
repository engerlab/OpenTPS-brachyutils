
from Controllers.dataLoaderController import DataLoaderController
from Controllers.api import API


def instantiateAPI(patientList):
    DataLoaderController(patientList)

    print('Methods instantiated:')
    print(API().getMethodsAsString())
