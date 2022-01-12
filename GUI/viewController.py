
import logging

from Core.event import Event
from GUI.MainWindow import MainWindow


class ViewController():
    def __init__(self, patientList):
        # Events
        self.crossHairEnabledSignal = Event(bool)
        self.currentPatientChangedSignal = Event(object)
        self.independentViewsEnabledSignal = Event(bool)
        self.lineWidgetEnabledSignal = Event(object)
        self.mainImageChangedSignal = Event(object)
        self.patientAddedSignal = Event(object)
        self.patientRemovedSignal = Event(object)
        self.showContourSignal = Event(object)
        self.windowLevelEnabledSignal = Event(bool)

        self._activePatients = [patient for patient in patientList.patients]
        self._crossHairEnabled = None
        self._currentPatient = None
        self._independentViewsEnabled = False
        self._lineWidgetEnabled = False
        self.multipleActivePatientsEnabled = False #TODO
        self._selectedImage = None
        self._windowLevelEnabled = None

        self.mainWindow = MainWindow(self)
        # this is useful if used with the signal emitted from the PatientDataTree in the setDataToDisplay function
        self.mainWindow.mainToolbar.patientDataPanel.patientDataTree.dataSelectedSignal.connect(self.setMainImage)


        self.logger = logging.getLogger(__name__)

        patientList.patientAddedSignal.connect(self.appendActivePatient)
        patientList.patientRemovedSignal.connect(self.appendActivePatient)

        self.numberOfViewerPanelElement = 0
        self.shownDataUIDsList = [] #this is to keep track of which data is currently shown, but not used yet

    @property
    def activePatient(self):
        if self.multipleActivePatientsEnabled:
            self.logger.exception('Cannot getActivePatient if multiple patients enabled')
            raise

    @property
    def activePatients(self):
        return self.activePatients

    # if self.multipleActivePatientsEnabled
    def appendActivePatient(self, patient):
        self.activePatients.append(patient)
        self.patientAddedSignal.emit(self.activePatients[-1])

    def removeActivePatient(self, patient):
        self.activePatients.remove(patient)
        self.patientRemovedSignal.emit(patient)

    @property
    def crossHairEnabled(self):
        return self._crossHairEnabled

    @crossHairEnabled.setter
    def crossHairEnabled(self, enabled):
        if enabled==self._crossHairEnabled:
            return

        if self._windowLevelEnabled and enabled:
            self.windowLevelEnabled = False

        self._crossHairEnabled = enabled
        self.crossHairEnabledSignal.emit(self._crossHairEnabled)

    @property
    def currentPatient(self):
        return self._currentPatient

    @currentPatient.setter
    def currentPatient(self, patient):
        self._currentPatient = patient
        self.currentPatientChangedSignal.emit(self._currentPatient)

    @property
    def independentViewsEnabled(self):
        return self._independentViewsEnabled

    @independentViewsEnabled.setter
    def independentViewsEnabled(self, enabled):
        if enabled==self._independentViewsEnabled:
            return

        self._independentViewsEnabled = enabled

        self.independentViewsEnabledSignal.emit(self._independentViewsEnabled)

    @property
    def lineWidgetEnabled(self):
        return self._lineWidgetEnabled

    @lineWidgetEnabled.setter
    def lineWidgetEnabled(self, enabled, callback=None):
        self._lineWidgetEnabled = enabled

        if self._lineWidgetEnabled:
            self.lineWidgetEnabledSignal.emit(callback)
        else:
            self.lineWidgetEnabledSignal.emit(False)

    @property
    def selectedImage(self):
        return self._selectedImage

    @selectedImage.setter
    def selectedImage(self, image):
        self._selectedImage = image

    def setMainImage(self, image):
        self.mainImageChangedSignal.emit(image)
        self.shownDataUIDsList.append(image.seriesInstanceUID)

    @property
    def windowLevelEnabled(self):
        return self._windowLevelEnabled

    @windowLevelEnabled.setter
    def windowLevelEnabled(self, enabled):
        if enabled==self._windowLevelEnabled:
            return

        if self._crossHairEnabled and enabled:
            self.crossHairEnabled = False

        self._windowLevelEnabled = enabled
        self.windowLevelEnabledSignal.emit(self._windowLevelEnabled)

    def showContour(self, contour):
        self.showContourSignal.emit(contour)
