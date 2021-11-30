
import logging

from PyQt5.QtCore import QObject, pyqtSignal

from Controllers.DataControllers.patientController import PatientController


class ViewController(QObject):
    patientAddedSignal = pyqtSignal(object)
    patientRemovedSignal = pyqtSignal(object)

    def __init__(self, patientListController):
        QObject.__init__(self)

        self.activePatientControllers = [PatientController(patient) for patient in patientListController.data]
        self.logger = logging.getLogger(__name__)
        self.multipleActivePatientsEnabled = False
        self._selectedImageController = None

        patientListController.patientAddedSignal.connect(self.appendActivePatientController)
        patientListController.patientRemovedSignal.connect(self.appendActivePatientController)

    # if self.multipleActivePatientsEnabled
    def appendActivePatientController(self, patientController):
        patientController = PatientController(patientController)

        self.activePatientControllers.append(patientController)
        self.patientAddedSignal.emit(self.activePatientControllers[-1])

    def removeActivePatientController(self, patientController):
        patientController = PatientController(patientController)

        self.activePatientControllers.remove(patientController)
        self.patientRemovedSignal.emit(patientController)

    def getActivePatientControllers(self):
        if self.multipleActivePatientsEnabled:
            self.logger.exception('Cannot getActivePatientController if multiple patients enabled')
            raise

    def getSelectedImageController(self):
        return self._selectedImageController

    def setSelectedImageController(self, imageController):
        self._selectedImageController = imageController

