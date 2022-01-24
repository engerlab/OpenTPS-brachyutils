
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from GUI.Viewer.Viewers.imageViewer import ImageViewer
from GUI.Viewer.Viewers.secondaryImageActions import SecondaryImageActions
from GUI.Viewer.dataViewerToolbar import DataViewerToolbar
from GUI.Viewer.Viewers.blackEmptyPlot import BlackEmptyPlot
from GUI.Viewer.Viewers.dvhPlot import DVHPlot
from GUI.Viewer.Viewers.profilePlot import ProfilePlot

class DataViewer(QWidget):
    DISPLAY_DVH = 'DVH'
    DISPLAY_NONE = 'None'
    DISPLAY_PROFILE = 'PROFILE'
    DISPLAY_SLICEVIEWER = 'SLICE'

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._currentViewer = None
        self._displayType = None
        self._dropEnabled = False
        self._mainLayout = QVBoxLayout(self)
        self._profileViewer = None
        self._secondaryActions = None
        self._sliceViewer = None
        self._toolbar = DataViewerToolbar()
        self._viewController = viewController

        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        self._toolbar.displayTypeSignal.connect(self._setDisplay)

        self._setToolbar(self._toolbar)
        self._setDisplay(self.DISPLAY_SLICEVIEWER)

        self._viewController.independentViewsEnabledSignal.connect(self._setDropEnabled)
        self._setDropEnabled(self._viewController.independentViewsEnabled)
        self._viewController.mainImageChangedSignal.connect(self._setMainImage)
        self._viewController.secondaryImageChangedSignal.connect(self._setSecondaryImage)

        # self.dynamicDataList = []

    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                self._setMainImage(self._viewController.selectedImage)
                return
        e.ignore()

    @property
    def currentViewer(self):
        return self._currentViewer

    def _setDisplay(self, displayType):
        if displayType==self._displayType:
            return

        if not (self._currentViewer is None):
            self._currentViewer.hide()

        if self._displayType == self.DISPLAY_SLICEVIEWER and displayType != self.DISPLAY_SLICEVIEWER:
            self._sliceViewer.qActions.hideAll()

        self._displayType = displayType

        if self._displayType==self.DISPLAY_DVH:
            self._currentViewer = DVHPlot()

        if self._displayType==self.DISPLAY_NONE:
            self._currentViewer = BlackEmptyPlot()

        if self._displayType==self.DISPLAY_PROFILE:
            if self._profileViewer is None:
                self._profileViewer = ProfilePlot(self._viewController)

            self._currentViewer = self._profileViewer

        if self._displayType==self.DISPLAY_SLICEVIEWER:
            if self._sliceViewer is None:
                self._sliceViewer = ImageViewer(self._viewController)
                for action in self._sliceViewer.qActions:
                    action.setParent(self._toolbar)
                    self._toolbar.addAction(action)

            self._sliceViewer.qActions.resetVisibility()

            self._currentViewer = self._sliceViewer

            self._setDropEnabled(self._dropEnabled)

        self._toolbar.handleDisplayChange(self._currentViewer)

        if not (self._currentViewer is None):
            self._mainLayout.removeWidget(self._currentViewer)

        self._mainLayout.addWidget(self._currentViewer)
        self._currentViewer.show()

    def _setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled and self._displayType==self.DISPLAY_SLICEVIEWER:
            self._currentViewer.setAcceptDrops(True)
            self._currentViewer.dragEnterEvent = lambda event: event.accept()
            self._currentViewer.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._currentViewer.setAcceptDrops(False)

    def _setMainImage(self, image):
        if hasattr(self._currentViewer, 'primaryImage'):    #why this if ?
            self._currentViewer.primaryImage = image

            if not(image is None):
                image.patient.imageRemovedSignal.connect(self._handleImageRemoved)

    def _setSecondaryImage(self, image):
        if hasattr(self._currentViewer, 'secondaryImage'):
            if self._currentViewer.secondaryImage == image:
                self._setSecondaryImage(None) # Currently default behavior but is it a good idea?
                return

            if image is None:
                oldImage = self._currentViewer.secondaryImage
                if oldImage is None:
                    return
            else:
                image.patient.imageRemovedSignal.connect(self._handleImageRemoved)

            self._currentViewer.secondaryImage = image

    def _handleImageRemoved(self, image):
        if hasattr(self._currentViewer, 'primaryImage') and self._currentViewer.primaryImage == image:
            self._setMainImage(None)

        if hasattr(self._currentViewer, 'secondaryImage') and self._currentViewer.secondaryImage == image:
            self._setSecondaryImage(None)

    def _setToolbar(self, toolbar):
        self._toolbar = toolbar
        self._mainLayout.addWidget(self._toolbar)
