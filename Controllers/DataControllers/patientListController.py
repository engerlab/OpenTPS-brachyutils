from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.dataController import DataController


class PatientListController(DataController):
    patientAdded = pyqtSignal(object)
    patientRemoved = pyqtSignal(object)
    a = []

    def __init__(self, patientList):
        DataController.__init__(self, patientList)

if __name__ == '__main__':
    p1 = PatientListController('jlj')
    print(p1.data)
    p2 = PatientListController('khkh')

    # will return false
    print(p1.patientAdded==p2.patientAdded)
    # will return true
    print(p1.a==p2.a)