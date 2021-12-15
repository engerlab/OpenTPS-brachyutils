from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController
from Controllers.DataControllers.patientController import PatientController


class PatientListController(DataController):
    patientAddedSignal = pyqtSignal(object)
    patientRemovedSignal = pyqtSignal(object)

    def __init__(self, patientList):
        super().__init__(patientList)

    def __getitem__(self, index):
        return PatientController(self.data[index])

    def __len__(self):
        return len(self.data)

    def append(self, patient):
        if isinstance(patient, PatientController):
            patient = patient.data

        self.data.append(patient)
        self.patientAddedSignal.emit(PatientController(patient))

    def remove(self, patient):
        if isinstance(patient, PatientController):
            patient = patient.data

        self.data.remove(patient)
        self.patientRemovedSignal.emit(PatientController(patient))

    def getPatientController(self, index):
        return PatientController(self.data.list[index])

    def getIndex(self, patient):
        if isinstance(patient, PatientController):
            patient = patient.data

        return self.data.list.index(patient)

    def getIndexFromPatientID(self, patientID):
        if patientID == "":
            return -1

        index = next((x for x, val in enumerate(self.data.list) if val.patientInfo.patientID == patientID), -1)
        return index

    def getIndexFromPatientName(self, patientName):
        if patientName == "":
            return -1

        index = next((x for x, val in enumerate(self.data.list) if val.patientInfo.name == patientName), -1)
        return index

