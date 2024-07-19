
import logging
from typing import Optional

from opentps.core.data.images import DoseImage, CTImage, MRImage
from opentps.core import Event
from opentps.gui.mainWindow import MainWindow
from opentps.gui.viewer.dataViewerComponents.profileWidget import ProfileWidget
from opentps.gui.viewer.dataViewer import DataViewer
from opentps.gui.viewer.dynamicDisplayController import DynamicDisplayController
from opentps.gui.viewer.viewerPanel import ViewerPanel


class ViewController():
    def __init__(self, patientList):
        # Events
        self.crossHairEnabledSignal = Event(bool)
        self.currentPatientChangedSignal = Event(object)
        self.independentViewsEnabledSignal = Event(bool)
        self.profileWidgetEnabledSignal = Event(object)
        self.mainImageChangedSignal = Event(object)
        self.dose1ChangedSignal = Event(object)
        self.dose2ChangedSignal = Event(object)
        self.patientAddedSignal = Event(object)
        self.patientRemovedSignal = Event(object)
        self.secondaryImageChangedSignal = Event(object)
        self.planChangedSignal = Event(object)
        self.showContourSignal = Event(object)
        self.windowLevelEnabledSignal = Event(bool)
        self.dropModeSignal = Event(object)
        self.droppedDataSignal = Event(object)
        self.displayLayoutTypeChangedSignal = Event(object)
        #self.dynamicViewerSwitchedOnSignal = Event(object)

        self.mainConfig = None

        self._activePatients = [patient for patient in patientList.patients]
        self._crossHairEnabled = None
        self._currentPatient = None
        self._dropMode = DataViewer.DropModes.DEFAULT
        self._droppedImage = None
        self._independentViewsEnabled = False
        self.profileWidgetCallback = ProfileWidget.ProfileWidgetCallback()
        self._profileWidgetEnabled = False
        self._mainImage = None
        self._dose1 = None
        self._dose2 = None
        self.multipleActivePatientsEnabled = False #TODO
        self._patientList = patientList
        self._plan = None
        self._selectedImage = None
        self._windowLevelEnabled = None
        self._displayLayout = ViewerPanel.LayoutTypes.DEFAULT
        self.shownDataUIDsList = []  # this is to keep track of which data is currently shown, but not used yet

        self.dynamicDisplayController = DynamicDisplayController(self)
        self.mainWindow = MainWindow(self)

        # self.dynamicDisplayController.connectViewerUnits(self.mainWindow.viewerPanel._viewerGrid)
        # self.dynamicDisplayController.setToolBar(self.mainWindow.viewerPanel._viewToolbar)

        self.logger = logging.getLogger(__name__)

        self._patientList.patientAddedSignal.connect(self._handleNewPatient)
        self._patientList.patientRemovedSignal.connect(self._handleRemovedPatient)

    def _handleNewPatient(self, patient):
        self._activePatients.append(patient)
        self.patientAddedSignal.emit(self._activePatients[-1])

        if self.currentPatient is None:
            self.currentPatient = patient

    def _displayCTOfCurrentPatient(self):
        if self.currentPatient is None:
            return
        
        ct = self.currentPatient.getPatientDataOfType(CTImage)
        if len(ct)>0:
            self.mainImage = ct[0]

    def _displayMRIOfCurrentPatient(self):
        if self.currentPatient is None:
            return

        mri = self.currentPatient.getPatientDataOfType(MRImage)
        if len(mri)>0:
            self.mainImage = mri[0]


    def _handleRemovedPatient(self, patient):
        self._activePatients.remove(patient)
        self.patientRemovedSignal.emit(patient)

        if self.currentPatient == patient:
            self.currentPatient = None

    @property
    def displayLayoutType(self):
        return self._displayLayout

    @displayLayoutType.setter
    def displayLayoutType(self, layout):
        if layout == self._displayLayout:
            return

        self._displayLayout = layout
        self.displayLayoutTypeChangedSignal.emit(self._displayLayout)

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
        previousPatient = self._currentPatient
        noPreviousPatient = previousPatient is None

        if patient == previousPatient:
            return

        self._currentPatient = patient

        if noPreviousPatient:
            self._displayCTOfCurrentPatient()
            self._displayMRIOfCurrentPatient()
            self._currentPatient.patientDataAddedSignal.connect(self._handleNewCTinFirstPatient)
            self._currentPatient.patientDataAddedSignal.connect(self._handleNewMRIinFirstPatient)
        else:
            previousPatient.patientDataAddedSignal.disconnect(self._handleNewCTinFirstPatient)
            previousPatient.patientDataAddedSignal.disconnect(self._handleNewMRIinFirstPatient)

        self.currentPatientChangedSignal.emit(self._currentPatient)

    def _handleNewCTinFirstPatient(self, data):
        if isinstance(data, CTImage):
            self._displayCTOfCurrentPatient()
    
    def _handleNewMRIinFirstPatient(self, data):
        if isinstance(data, MRImage):
            self._displayMRIOfCurrentPatient()

    @property
    def dropMode(self):
        return self._dropMode

    @dropMode.setter
    def dropMode(self, mode):
        if mode == self._dropMode:
            return

        self._dropMode = mode
        self.dropModeSignal.emit(self._dropMode)

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
    def profileWidgetEnabled(self):
        return self._profileWidgetEnabled

    @profileWidgetEnabled.setter
    def profileWidgetEnabled(self, enabled):
        self._profileWidgetEnabled = enabled
        self.profileWidgetEnabledSignal.emit(self._profileWidgetEnabled)

    @property
    def mainImage(self):
        if self.independentViewsEnabled:
            # mainImage is only available when only one image can be shown
            raise Exception("mainImage is only available when only one image can be shown")
        return self._mainImage

    @mainImage.setter
    def mainImage(self, image):
        if self.independentViewsEnabled:
            # mainImage is only available when only one image can be shown
            raise Exception("mainImage is only available when only one image can be shown")

        self._mainImage = image
        self.mainImageChangedSignal.emit(self._mainImage)
        # self.dynamicOrStaticModeChangedSignal.emit(self._mainImage)
        self.shownDataUIDsList.append(self._mainImage.seriesInstanceUID)

    @property
    def secondaryImage(self):
        if self.independentViewsEnabled:
            # secondaryImage is only available when only one image can be shown
            raise("secondaryImage is only available when only one image can be shown")
        return self._secondaryImage

    @secondaryImage.setter
    def secondaryImage(self, image):
        if self.independentViewsEnabled:
            # secondaryImage is only available when only one image can be shown
            raise Exception("secondaryImage is only available when only one image can be shown")

        self._secondaryImage = image
        self.secondaryImageChangedSignal.emit(self._secondaryImage)

    @property
    def dose1(self) -> Optional[DoseImage]:
        return self._dose1

    @dose1.setter
    def dose1(self, image:Optional[DoseImage]):
        if image == self._dose1:
            return

        self._dose1 = image
        self.dose1ChangedSignal.emit(self._dose1)

    @property
    def dose2(self) -> Optional[DoseImage]:
        return self._dose2

    @dose2.setter
    def dose2(self, image: Optional[DoseImage]):
        if image == self._dose2:
            return

        self._dose2 = image
        self.dose2ChangedSignal.emit(self._dose2)

    @property
    def plan(self):
        if self.independentViewsEnabled:
            # secondaryImage is only available when only one image can be shown
            raise ("plan is only available when only one image can be shown")
        return self._plan

    @plan.setter
    def plan(self, plan):
        if self.independentViewsEnabled:
            # secondaryImage is only available when only one image can be shown
            raise ("plan is only available when only one image can be shown")

        self._plan = plan
        self.planChangedSignal.emit(self._plan)

    @property
    def droppedImage(self):
        if self.independentViewsEnabled:
            # droppedImage is only available when only one image can be shown
            raise()

        return self._droppedImage

    @droppedImage.setter
    def droppedImage(self, image):
        if self.independentViewsEnabled:
            # droppedImage is only available when only one image can be shown
            raise()

        self._droppedImage = image
        self.droppedDataSignal.emit(self._droppedImage)

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
