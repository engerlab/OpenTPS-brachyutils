
import logging

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QToolBox

from Controllers.DataControllers.patientController import PatientController
from GUI.Panels.mainToolbar import MainToolbar
from GUI.Panels.viewerPanel.viewerPanel import ViewerPanel
from GUI.ViewControllers.viewerPanelControllers.viewerPanelController import ViewerPanelController


class ViewController(QObject):
    patientAddedSignal = pyqtSignal(object)
    patientRemovedSignal = pyqtSignal(object)

    def __init__(self, patientListController, mainWindow):
        QObject.__init__(self)

        self.mainWindow = mainWindow

        self.activePatientControllers = [PatientController(patient) for patient in patientListController.data]
        self.logger = logging.getLogger(__name__)
        self.multipleActivePatientsEnabled = False
        self._selectedImageController = None

        mainToolbar = MainToolbar(self)
        self.mainWindow.setLateralToolbar(mainToolbar)

        viewerPanel = ViewerPanel()
        viewerPanelController = ViewerPanelController(viewerPanel, self)
        self.mainWindow.setMainPanel(viewerPanel)

        patientListController.patientAddedSignal.connect(self.appendActivePatientController)
        patientListController.patientRemovedSignal.connect(self.appendActivePatientController)

        #For Damien:
        #Define mainImageSelectedSignal in mainToolbar
        #mainToolbar.mainImageSelectedSignal.connect(viewerPanelController.setMainImage)

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
