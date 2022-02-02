
from API.dataLoaderAPI import DataLoaderAPI
from API.api import API
from API.dynamicSequenceAPI import DynamicSequenceController


def instantiateAPI(patientList):
    API.patientList = patientList

    DataLoaderAPI(patientList)
    DynamicSequenceController(patientList)


