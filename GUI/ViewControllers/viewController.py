
import logging

from PyQt5.QtCore import QObject, pyqtSignal

from Controllers.DataControllers.patientController import PatientController
from GUI.MainWindow import *


class ViewController(QObject):
    crossHairEnabledSignal = pyqtSignal(bool)
    independentViewsEnabledSignal = pyqtSignal(bool)
    lineWidgetEnabledSignal = pyqtSignal(object)
    mainImageChangedSignal = pyqtSignal(object)
    patientAddedSignal = pyqtSignal(object)
    patientRemovedSignal = pyqtSignal(object)
    showContourSignal = pyqtSignal(object)
    windowLevelEnabledSignal = pyqtSignal(bool)

    def __init__(self, patientListController):#, mainWindow):
        QObject.__init__(self)

        self._crossHairEnabled = None
        self._independentViewsEnabled = False
        self._lineWidgetEnabled = False
        self.mainWindow = MainWindow(self)
        self._windowLevelEnabled = None

        self.activePatientControllers = [PatientController(patient) for patient in patientListController.data]
        self.logger = logging.getLogger(__name__)
        self.multipleActivePatientsEnabled = False
        self._selectedImageController = None

        # mainToolbar = MainToolbar(self)
        # self.mainWindow.setLateralToolbar(mainToolbar)
        #
        # viewerPanel = ViewerPanel(self)
        # self.mainWindow.setMainPanel(viewerPanel)

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

    def getActivePatientControllers(self):
        if self.multipleActivePatientsEnabled:
            self.logger.exception('Cannot getActivePatientController if multiple patients enabled')
            raise

    def getCrossHairEnabled(self):
        return self._crossHairEnabled

    def getIndependentViewsEnabled(self):
        return self._independentViewsEnabled

    def getSelectedImageController(self):
        return self._selectedImageController

    def removeActivePatientController(self, patientController):
        patientController = PatientController(patientController)

        self.activePatientControllers.remove(patientController)
        self.patientRemovedSignal.emit(patientController)

    def setCrossHairEnabled(self, enabled):
        if enabled==self._crossHairEnabled:
            return

        if self._windowLevelEnabled and enabled:
            self.setWindowLevelEnabled(False)

        self._crossHairEnabled = enabled
        self.crossHairEnabledSignal.emit(self._crossHairEnabled)

    def setIndependentViewsEnabled(self, enabled):
        if enabled==self._independentViewsEnabled:
            return

        self._independentViewsEnabled = enabled

        self.independentViewsEnabledSignal.emit(self._independentViewsEnabled)

    def setLineWidgetEnabled(self, enabled, callback=None):
        self._lineWidgetEnabled = enabled

        if self._lineWidgetEnabled:
            self.lineWidgetEnabledSignal.emit(callback)
        else:
            self.lineWidgetEnabledSignal.emit(False)

    def setMainImage(self, imageController):
        self.mainImageChangedSignal.emit(imageController)

    def setSelectedImageController(self, imageController):
        self._selectedImageController = imageController

    def setWindowLevelEnabled(self, enabled):
        if enabled==self._windowLevelEnabled:
            return

        if self._crossHairEnabled and enabled:
            self.setCrossHairEnabled(False)

        self._windowLevelEnabled = enabled
        self.windowLevelEnabledSignal.emit(self._windowLevelEnabled)

    def showContour(self, contourController):
        self.showContourSignal.emit(contourController)
