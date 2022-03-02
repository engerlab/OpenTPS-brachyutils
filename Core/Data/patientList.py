from typing import Sequence

from Core.Data.patient import Patient
from Core.Data.patientData import PatientData
from Core.api import API
from Core.event import Event
import copy


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

        index = next((x for x, val in enumerate(self._patients) if val.patientInfo.patientID == patientID), -1)
        return index

    def getIndexFromPatientName(self, patientName:str) -> int:
        if patientName == "":
            return -1

        index = next((x for x, val in enumerate(self._patients) if val.patientInfo.name == patientName), -1)
        return index

    def getPatientByData(self, patientData:PatientData) -> Patient:
        for patient in self._patients:
            if patient.hasPatientData(patientData):
                return patient

        return None

    def getPatientByPatientId(self, id:str) -> Patient:
        for i, patient in enumerate(self._patients):
            if patient.patientInfo.patientID==id:
                return patient

    @API.loggedViaAPI
    def remove(self, patient:Patient):
        self._patients.remove(patient)
        self.patientRemovedSignal.emit(patient)

    def dumpableCopy(self):

        dumpablePatientListCopy = PatientList()
        for patient in self._patients:
            dumpablePatientListCopy._patients.append(patient.dumpableCopy())

        return dumpablePatientListCopy()
