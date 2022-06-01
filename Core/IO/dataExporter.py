import logging
import os

from Core.Data.Images.image3D import Image3D
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.patient import Patient
from Core.IO import dicomIO, mhdIO
from Core.api import API

logger = logging.getLogger(__name__)

@API.loggedViaAPI
def exportPatientAsDicom(patient:Patient, folderPath:str):
    for data in patient.patientData:
        if isinstance(data, RTPlan):
            filePath = _checkAndRenameFile(folderPath, data.name + '.dcm')
            dicomIO.writeRTPlan(data, os.path.join(folderPath, filePath))
        elif isinstance(data, Image3D):
            logger.warning(data.__class__.__name__ + ' cannot be exported in dicom. Exporting in MHD instead.')
            filePath = _checkAndRenameFile(folderPath, data.name + '.mhd')
            mhdIO.exportImageMHD(os.path.join(folderPath, filePath), data)
        else:
            logger.warning(data.__class__.__name__ + ' cannot be exported')


def _checkAndRenameFile(folderPath:str, fileName:str) -> str:
    if not os.path.isfile(os.path.join(folderPath, fileName)):
        return fileName

    numb = 1
    while True:
        newPath = "{0}_{2}{1}".format(*os.path.splitext(fileName) + (numb,))
        if os.path.isfile(os.path.join(folderPath, newPath)):
            numb += 1
        else:
            return newPath
