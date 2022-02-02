from pydicom.uid import generate_uid

from API.api import API
from Core.Data.dynamic3DSequence import Dynamic3DSequence


@API.apiClass
class DynamicSequenceController:
    patientList = None

    def __init__(self, patientList):
        self.patientList = patientList

    @staticmethod
    @API.apiMethod
    def createDynamic3DSequence(selectedImages, newName):

        newSeq = Dynamic3DSequence(dyn3DImageList=selectedImages, name=newName)

        for image in selectedImages:
            patient = image.patient
            patient.removeImage(image)

        newSeq.seriesInstanceUID = generate_uid()
        patient.appendDyn3DSeq(newSeq)