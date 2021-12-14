from PyQt5.QtCore import QObject

from Controllers.DataControllers.patientListController import PatientListController


class ModelController(QObject):
    patientListController = None

    def __init__(self, patientListController=None):
        QObject.__init__(self)

        if not(patientListController is None):
            ModelController.patientListController = PatientListController(patientListController)

        if self.patientListController is None:
            raise ValueError('Argument patientListController should not be None')
