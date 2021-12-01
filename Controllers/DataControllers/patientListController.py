from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController
from Controllers.DataControllers.patientController import PatientController


class PatientListController(DataController):
    patientAddedSignal = pyqtSignal(object)
    patientRemovedSignal = pyqtSignal(object)

    def __init__(self, patientList):
        super().__init__(patientList)

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

    def getIndex(self, patient):
        if isinstance(patient, PatientController):
            patient = patient.data

        self.data.list.index(patient)






if __name__ == '__main__':
    p1 = PatientListController('jlj')
    p2 = PatientListController('khkh')

    # will return false
    print(p1.patientAddedSignal == p2.patientAddedSignal)