from abc import abstractmethod

from PyQt5.QtCore import pyqtSignal, QObject

from Controllers.DataControllers.patientController import PatientController


class PatientDataPanelController(QObject):
    currentPatientChangedSignal = pyqtSignal(object)
    patientAddedSignal = pyqtSignal(object)
    patientRemovedSignal = pyqtSignal(object)


    def __init__(self, viewController):
        QObject.__init__(self)

        self._viewController = viewController
        self._currentPatientController = None

        self._viewController.patientAddedSignal.connect(self.patientAddedSignal.emit)
        self._viewController.patientAddedSignal.connect(self._handleNewPatient)

        self._viewController.patientRemovedSignal.connect(self.patientRemovedSignal.emit)
        self._viewController.patientRemovedSignal.connect(self._handleRemovedPatient)

    def _handleNewPatient(self, patientController):
        if self._currentPatientController is None:
            self.setCurrentPatientController(patientController)

    def _handleRemovedPatient(self, patientController):
        if self._currentPatientController == patientController:
            self.setCurrentPatientController(None)

    def getCurrentPatientController(self):
        return PatientController(self._currentPatientController)

    def getSelectedImageController(self):
        return self._viewController.getSelectedImageController()

    @abstractmethod
    def getLeftClickMenu(self):
        pass

    def setCurrentPatientController(self, patientController):
        self._currentPatientController = patientController
        self.currentPatientChangedSignal.emit(self._currentPatientController)

    def setSelectedImageController(self, imageController):
        self._viewController.setSelectedImageController(imageController)

