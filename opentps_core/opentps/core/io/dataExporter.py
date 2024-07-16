import logging
import os
from enum import Enum
from typing import Sequence

from opentps.core.data.images import Image3D
from opentps.core.data.plan import RTPlan
from opentps.core.data import Patient
from opentps.core.io import mhdIO
from opentps.core.io import dicomIO
from opentps.core.data.images import CTImage,DoseImage
from opentps.core.data import RTStruct


logger = logging.getLogger(__name__)


class ExportTypes(Enum):
    """
    Enumeration of the different export types
    """
    DICOM = "Dicom"
    MHD = "MHD"
    MCSQUARE = "MCsquare"
    PICKLE = "Pickle"

class DataType:
    """
    Class to store the export types for a specific data type

    Attributes
    ----------
    name:str
        The name of the data type
    exportTypes:Sequence
        The export types for this data type
    exportType:ExportTypes
        The export type to use

    """
    def __init__(self, name:str, exportTypes:Sequence):
        self.name = name
        self.exportTypes = exportTypes
        self.exportType = ExportTypes.DICOM

class ExportConfig:
    """
    gives all the export configuration to store the data (depending on the data type)

    Attributes
    ----------

    imageConfig:DataType
        The image data type configuration
    doseConfig:DataType
        The dose data type configuration
    planConfig:DataType
        The plan data type configuration
    contoursConfig:DataType
        The contours data type configuration
    otherConfig:DataType
        The other data type configuration

    """
    def __init__(self):
        self._types = [DataType("Image", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.MCSQUARE, ExportTypes.PICKLE]),
                       DataType("Dose", [ExportTypes.DICOM, ExportTypes.MHD, ExportTypes.PICKLE]),
                       DataType("Plan", [ExportTypes.DICOM, ExportTypes.MCSQUARE, ExportTypes.PICKLE]),
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
    """
    Exports the patient data to the given folder path.

    Parameters
    ----------

    patient:Patient
        The patient to export
    folderPath:str
        The folder path to export to
    config:ExportConfig
        The export configuration
    """
    for data in patient.patientData:
        if isinstance(data, RTPlan) and config.planConfig.exportType is not None:
            exportPlan(data, folderPath, config.planConfig.exportType)
        elif isinstance(data, CTImage) and config.imageConfig.exportType is not None:
            exportImage(data, folderPath, config.imageConfig.exportType)
        elif isinstance(data, DoseImage) and config.doseConfig.exportType is not None:
            exportImage(data, folderPath, config.doseConfig.exportType)
        elif isinstance(data, RTStruct) and config.contoursConfig.exportType is not None:
            exportContours(data, folderPath, config.contoursConfig.exportType)
        else:
            logger.warning(data.__class__.__name__ + ' cannot be exported or was not checked')

def exportImage(image:Image3D, folderPath:str, imageConfig:ExportTypes):
    """
    Exports the image to the given folder path.

    Parameters
    ----------
    image:Image3D
        The image to export
    folderPath:str
        The folder path to export to
    imageConfig:ExportTypes
        The export configuration
    """
    if imageConfig == ExportTypes.MHD:
        filePath = _checkAndRenameFile(folderPath, image.__class__.__name__ + '_' + image.name + '.mhd')
        mhdIO.exportImageMHD(os.path.join(folderPath, filePath), image)
    elif imageConfig == ExportTypes.DICOM:
        if isinstance(image, DoseImage):
            dicomIO.writeRTDose(image, folderPath)
        if isinstance(image, CTImage):
            dicomIO.writeDicomCT(image, folderPath)
    else:
        logger.warning(image.__class__.__name__ + ' cannot be exported in dicom. Exporting in MHD instead.')
        filePath = _checkAndRenameFile(folderPath, image.__class__.__name__ + '_' + image.name + '.mhd')
        mhdIO.exportImageMHD(os.path.join(folderPath, filePath), image)

def exportPlan(plan:RTPlan, folderPath:str, planConfig:ExportTypes):
    """
    Exports the plan to the given folder path.

    Parameters
    ----------
    plan:RTPlan
        The plan to export
    folderPath:str
        The folder path to export to
    planConfig:ExportTypes
        The export configuration
    """
    if planConfig == ExportTypes.DICOM:
        dicomIO.writeRTPlan(plan, folderPath)
    else:
        raise NotImplementedError
    
def exportContours(contours:RTStruct, folderPath:str, contoursConfig:ExportTypes):
    """
    Exports the plan to the given folder path.

    Parameters
    ----------
    contours:RTStruct
        The contours to export
    folderPath:str
        The folder path to export to
    contoursConfig:ExportTypes
        The export configuration
    """
    if contoursConfig == ExportTypes.DICOM:
        dicomIO.writeRTStruct(contours, folderPath)
    else:
        raise NotImplementedError    

def exportPatientAsDicom(patient:Patient, folderPath:str):
    """
    Exports the patient data to the given folder path as dicom.

    Parameters
    ----------
    patient:Patient
        The patient to export
    folderPath:str
        The folder path to export to

    """
    for data in patient.patientData:
        if isinstance(data, RTPlan):
            exportPlan(data, folderPath, ExportTypes.DICOM)
        elif isinstance(data, RTStruct):
            exportContours(data, folderPath, ExportTypes.DICOM)
        elif isinstance(data, Image3D):
            exportImage(data, folderPath, ExportTypes.DICOM)
        else:
            logger.warning(data.__class__.__name__ + ' cannot be exported')


def _checkAndRenameFile(folderPath:str, fileName:str) -> str:
    """
    Checks if the file already exists in the folder path and renames it if it does.

    Parameters
    ----------
    folderPath:str
        The folder path to check in
    fileName:str
        The file name to check

    Returns
    -------
    fileName:str
        The new file name
    """
    if not os.path.isfile(os.path.join(folderPath, fileName)):
        return fileName

    numb = 1
    while True:
        newPath = "{0}_{2}{1}".format(*os.path.splitext(fileName) + (numb,))
        if os.path.isfile(os.path.join(folderPath, newPath)):
            numb += 1
        else:
            return newPath
