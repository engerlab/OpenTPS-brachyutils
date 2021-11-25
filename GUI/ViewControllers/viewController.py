
import logging

from PyQt5.QtCore import QObject, pyqtSignal


class ViewController(QObject):
    currentPatientChangedSignal = pyqtSignal(object)

    def __init__(self, patientListController):
        QObject.__init__(self)

        self.activePatientControllers = []
        self.logger = logging.getLogger(__name__)
        self.multipleActivePatientsEnabled = False
        self._patientListController = patientListController

    # if self.multipleActivePatientsEnabled
    def appendActivePatientController(self, patientController):
        self.activePatientControllers.append(patientController)

    def getPatientListController(self):
        return self._patientListController

    def getActivePatientController(self):
        if self.multipleActivePatientsEnabled:
            self.logger.exception('Cannot getActivePatientController if multiple patients enabled')
            raise

    # if not self.multipleActivePatientsEnabled
    def setActivePatientController(self, patientController):
        self.activePatientControllers = [patientController]
        self.currentPatientChangedSignal.emit(self.activePatientControllers[0])

