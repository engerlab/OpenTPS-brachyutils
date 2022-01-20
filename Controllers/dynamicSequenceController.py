from pydicom.uid import generate_uid

from Controllers.api import API
from Core.Data.dynamic3DSequence import Dynamic3DSequence


class DynamicSequenceController:
    def __init__(self, patientList):
        self._patientList = patientList

        API.registerToAPI(self.createDynamic3DSequence.__name__, self.createDynamic3DSequence)

    def createDynamic3DSequence(self, selectedImages, newName):
        newSeq = Dynamic3DSequence()
        newSeq.name = newName
        newSeq.seriesInstanceUID = generate_uid()

        for i, image in enumerate(selectedImages):
            newSeq.dyn3DImageList.append(image)
            patient = image.patient
            patient.removeImage(image)

        patient.appendDyn3DSeq(newSeq)