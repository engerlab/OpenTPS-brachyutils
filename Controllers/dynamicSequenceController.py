from pydicom.uid import generate_uid

from Controllers.api import API
from Core.Data.dynamic3DSequence import Dynamic3DSequence


@API.apiClass
class DynamicSequenceController:
    patientList = None

    def __init__(self, patientList):
        self.patientList = patientList

    @staticmethod
    @API.apiMethod
    def createDynamic3DSequence(selectedImages, newName):
        newSeq = Dynamic3DSequence()
        newSeq.name = newName
        newSeq.seriesInstanceUID = generate_uid()

        for i, image in enumerate(selectedImages):
            newSeq.dyn3DImageList.append(image)
            patient = image.patient
            patient.removeImage(image)

        patient.appendDyn3DSeq(newSeq)