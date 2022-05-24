import logging
import os

from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.patient import Patient
from Core.IO import dicomIO
from Core.api import API

logger = logging.getLogger(__name__)

@API.loggedViaAPI
def exportPatientAsDicom(patient:Patient, folderPath):
    for data in patient.patientData:
        if isinstance(data, RTPlan):
            filePath = _checkAndRenameFile(folderPath, data.name + '.dcm')
            dicomIO.writeRTPlan(data, os.path.join(folderPath, filePath))
        else:
            logger.warning(data.__class__.__name__ + ' cannot be exported')


def _checkAndRenameFile(folderPath:str, fileName:str) -> str:
    if not os.path.isfile(os.path.join(folderPath, fileName)):
        return fileName

    numb = 1
    while True:
        newPath = "{0}_{2}{1}".format(*os.path.splitext(fileName) + (numb,))
        print(os.path.join(folderPath, newPath))
        if os.path.isfile(os.path.join(folderPath, newPath)):
            numb += 1
        else:
            return newPath
