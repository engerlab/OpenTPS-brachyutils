from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController


class PatientListController(DataController):
    patientAdded = pyqtSignal(object)
    patientRemoved = pyqtSignal(object)

    def __init__(self, patientList):
        super().__init__(patientList)

    def append(self, patient):
        self.data.append(patient)
        self.patientAdded.emit(patient)

    def remove(self, patient):
        self.data.remove(patient)
        self.patientRemoved.emit(patient)






if __name__ == '__main__':
    p1 = PatientListController('jlj')
    p2 = PatientListController('khkh')

    # will return false
    print(p1.patientAdded==p2.patientAdded)