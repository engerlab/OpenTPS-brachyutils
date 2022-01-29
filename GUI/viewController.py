
import logging

from Core.event import Event
from GUI.MainWindow import MainWindow
from GUI.Viewer.dynamicDisplayController import DynamicDisplayController

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
        self.secondaryImageChangedSignal = Event(object)
        self.showContourSignal = Event(object)
        self.windowLevelEnabledSignal = Event(bool)

        self._activePatients = [patient for patient in patientList.patients]
        self._crossHairEnabled = None
        self._currentPatient = None
        self._independentViewsEnabled = False
        self.lineWidgetCallback = lambda : None
        self._lineWidgetEnabled = False
        self._mainImage = None
        self.multipleActivePatientsEnabled = False #TODO
        self._patientList = patientList
        self._selectedImage = None
        self._windowLevelEnabled = None

        self.mainWindow = MainWindow(self)
        self.dynamicDisplayController = DynamicDisplayController(self)
        self.dynamicDisplayController.connectViewerUnits(self.mainWindow.viewerPanel._viewerGrid)
        self.dynamicDisplayController.setToolBar(self.mainWindow.viewerPanel._viewToolbar)

        self.logger = logging.getLogger(__name__)

        self._patientList.patientAddedSignal.connect(self.appendActivePatient)
        self._patientList.patientRemovedSignal.connect(self.appendActivePatient)

        self.shownDataUIDsList = [] #this is to keep track of which data is currently shown, but not used yet

    @property
    def patientList(self):
        return self._patientList

    @property
    def activePatient(self):
        if self.multipleActivePatientsEnabled:
            self.logger.exception('Cannot getActivePatient if multiple patients enabled')
            raise

        if len(self._activePatients)>1:
            self.logger.exception('Multiple patients disabled but more than one active patient')
            raise

        return self._activePatients[0]

    @property
    def activePatients(self):
        return [patient for patient in self._activePatients]

    # if self.multipleActivePatientsEnabled
    def appendActivePatient(self, patient):
        self._activePatients.append(patient)
        self.patientAddedSignal.emit(self._activePatients[-1])

    def removeActivePatient(self, patient):
        self._activePatients.remove(patient)
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
        if enabled == self._independentViewsEnabled:
            return

        self._independentViewsEnabled = enabled

        self.independentViewsEnabledSignal.emit(self._independentViewsEnabled)

    @property
    def lineWidgetEnabled(self):
        return self._lineWidgetEnabled

    @lineWidgetEnabled.setter
    def lineWidgetEnabled(self, enabled):
        self._lineWidgetEnabled = enabled
        self.lineWidgetEnabledSignal.emit(self._lineWidgetEnabled)

    @property
    def mainImage(self):
        if self.independentViewsEnabled:
            # mainImage is only available when only one image can be shown
            raise()

    @mainImage.setter
    def mainImage(self, image):
        self._mainImage = image
        self.mainImageChangedSignal.emit(self._mainImage)
        # self.dynamicOrStaticModeChangedSignal.emit(self._mainImage)
        self.shownDataUIDsList.append(self._mainImage.seriesInstanceUID)

    @property
    def secondaryImage(self):
        if self.independentViewsEnabled:
            # mainImage is only available when only one image can be shown
            raise()

    @secondaryImage.setter
    def secondaryImage(self, image):
        self._secondaryImage = image
        self.secondaryImageChangedSignal.emit(self._secondaryImage)

    @property
    def selectedImage(self):
        return self._selectedImage

    @selectedImage.setter
    def selectedImage(self, image):
        self._selectedImage = image

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
