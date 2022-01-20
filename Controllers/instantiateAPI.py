
from Controllers.dataLoaderController import DataLoaderController
from Controllers.api import API


def instantiateAPI(patientList):
    API.patientList = patientList

    DataLoaderController(patientList)

    print('Methods instantiated:')
    print(API.getMethodsAsString())
