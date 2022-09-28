
__all__ = ['PatientList']


from typing import Sequence

from opentps.core.data._patient import Patient
from opentps.core.data._patientData import PatientData
from opentps.core import Event


class PatientList():
    def __init__(self):
        self.patientAddedSignal = Event(object)
        self.patientRemovedSignal = Event(object)

        self._patients = []

    def __getitem__(self, index) -> Patient:
        return self._patients[index]

    def __len__(self):
        return len(self._patients)

    @property
    def patients(self) -> Sequence[Patient]:
        # Doing this ensures that the user can't append directly to patients
        return [patient for patient in self._patients]

    def append(self, patient:Patient):
        self._patients.append(patient)
        self.patientAddedSignal.emit(self._patients[-1])

    def getIndex(self, patient:Patient) -> int:
        return self._patients.index(patient)

    def getIndexFromPatientID(self, patientID:str) -> int:
        if patientID == "":
            return -1

        index = next((x for x, patient in enumerate(self._patients) if patient.id == patientID), -1)
        return index

    def getIndexFromPatientName(self, patientName:str) -> int:
        if patientName == "":
            return -1

        index = next((x for x, patient in enumerate(self._patients) if patient.name == patientName), -1)
        return index

    def getPatientByData(self, patientData:PatientData) -> Patient:
        for patient in self._patients:
            if patient.hasPatientData(patientData):
                return patient

        return None

    def getPatientByPatientId(self, id:str) -> Patient:
        for i, patient in enumerate(self._patients):
            if patient.id==id:
                return patient
        raise Exception('Patient not found')

    def remove(self, patient:Patient):
        self._patients.remove(patient)
        self.patientRemovedSignal.emit(patient)

    def dumpableCopy(self):

        dumpablePatientListCopy = PatientList()
        for patient in self._patients:
            dumpablePatientListCopy._patients.append(patient.dumpableCopy())

        return dumpablePatientListCopy()
