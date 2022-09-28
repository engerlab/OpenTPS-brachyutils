import logging
import os
from enum import Enum
from typing import Sequence

from opentps.core.data.images import Image3D
from opentps.core.data.plan import RTPlan
from opentps.core.data import Patient
from opentps.core.io import mhdIO
from opentps.core.io import dicomIO

logger = logging.getLogger(__name__)


class ExportTypes(Enum):
    DICOM = "Dicom"
    MHD = "MHD"
    MCSQUARE = "MCsquare"
    PICKLE = "Pickle"

class DataType:
    def __init__(self, name:str, exportTypes:Sequence):
        self.name = name
        self.exportTypes = exportTypes
        self.exportType = ExportTypes.DICOM

class ExportConfig:
    def __init__(self):
        self._types = [DataType("Image", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.MCSQUARE, ExportTypes.PICKLE]),
                       DataType("Dose", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.PICKLE]),
                       DataType("plan", [ExportTypes.DICOM, ExportTypes.MCSQUARE, ExportTypes.PICKLE]),
                       DataType("Contours", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.PICKLE]),
                       DataType("Other", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.MCSQUARE, ExportTypes.PICKLE])]

    def __len__(self):
        return len(self._types)

    def __getitem__(self, item):
        return self._types[item]

    @property
    def imageConfig(self) -> DataType:
        return self[0]

    @property
    def doseConfig(self) -> DataType:
        return self[1]

    @property
    def planConfig(self) -> DataType:
        return self[2]

    @property
    def contoursConfig(self) -> DataType:
        return self[3]

    @property
    def otherConfig(self) -> DataType:
        return self[4]

def exportPatient(patient:Patient, folderPath:str, config:ExportConfig):
    for data in patient.patientData:
        if isinstance(data, RTPlan):
            exportPlan(data, folderPath, config.planConfig.exportType)
        elif isinstance(data, Image3D):
            exportImage(data, folderPath, config.imageConfig.exportType)
        else:
            logger.warning(data.__class__.__name__ + ' cannot be exported')

def exportImage(image:Image3D, folderPath:str, imageConfig:ExportTypes):
    if imageConfig == ExportTypes.MHD:
        filePath = _checkAndRenameFile(folderPath, image.name + '.mhd')
        mhdIO.exportImageMHD(os.path.join(folderPath, filePath), image)
    else:
        logger.warning(image.__class__.__name__ + ' cannot be exported in dicom. Exporting in MHD instead.')
        filePath = _checkAndRenameFile(folderPath, image.name + '.mhd')
        mhdIO.exportImageMHD(os.path.join(folderPath, filePath), image)

def exportPlan(plan:RTPlan, folderPath:str, planConfig:ExportTypes):
    if planConfig == ExportTypes.DICOM:
        filePath = _checkAndRenameFile(folderPath, plan.name + '.dcm')
        dicomIO.writeRTPlan(plan, os.path.join(folderPath, filePath))
    else:
        raise NotImplementedError

def exportPatientAsDicom(patient:Patient, folderPath:str):
    for data in patient.patientData:
        if isinstance(data, RTPlan):
            exportPlan(data, folderPath, ExportTypes.DICOM)
        elif isinstance(data, Image3D):
            exportImage(data, folderPath, ExportTypes.DICOM)
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
