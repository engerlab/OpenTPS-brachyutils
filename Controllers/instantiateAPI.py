
from Controllers.dataLoaderController import DataLoaderController
from Controllers.api import API
from Controllers.dynamicSequenceController import DynamicSequenceController


def instantiateAPI(patientList):
    API.patientList = patientList

    DataLoaderController(patientList)
    DynamicSequenceController(patientList)

    print('Methods instantiated:')
    print(API.getMethodsAsString())
