from PyQt5.QtCore import QObject, pyqtSignal

from GUI.Viewers.blackEmptyPlot import BlackEmptyPlot
from GUI.Viewers.dvhPlot import DVHPlot
from GUI.Viewers.profilePlot import ProfilePlot
from GUI.Viewers.sliceViewer import SliceViewerVTK


class GridElementController(QObject):
    DISPLAY_DVH = 'DVH'
    DISPLAY_NONE = 'None'
    DISPLAY_PROFILE = 'PROFILE'
    DISPLAY_SLICEVIEWER = 'SLICE'

    displayChangedSignal = pyqtSignal(object)

    def __init__(self, viewerPanelController):
        QObject.__init__(self)

        self._displayType = None
        self._dropEnabled = False
        self._currentView = None
        self._sliceViewer = None
        self._viewerPanelController = viewerPanelController

        self.setDisplayType(self.DISPLAY_SLICEVIEWER)
        self._viewerPanelController.independentViewsEnabledSignal.connect(self.setDropEnabled)

    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                if hasattr(self._currentView, 'setMainImage'):
                    self.setMainImage(self.getSelectedImageController())
                return
        e.ignore()

    def getDisplayView(self):
        return self._currentView

    def getSelectedImageController(self):
        print(self._viewerPanelController.getSelectedImageController().getName())
        return self._viewerPanelController.getSelectedImageController()

    def setDisplayType(self, displayType):
        if displayType==self._displayType:
            return

        self._displayType = displayType

        if self._displayType==self.DISPLAY_DVH:
            self._currentView = DVHPlot()

        if self._displayType==self.DISPLAY_NONE:
            self._currentView = BlackEmptyPlot()

        if self._displayType==self.DISPLAY_PROFILE:
            self._currentView = ProfilePlot()
            self._currentView.newProfileSignal.connect(self._viewerPanelController.setLineWidgetEnabled)

        if self._displayType==self.DISPLAY_SLICEVIEWER:
            if self._sliceViewer is None:
                self._sliceViewer = SliceViewerVTK()

            self._currentView = self._sliceViewer

            self._viewerPanelController.crossHairEnabledSignal.connect(self._currentView.setCrossHairEnabled)
            self._viewerPanelController.windowLevelEnabledSignal.connect(self._currentView.setWWLEnabled)
            self._viewerPanelController.lineWidgetEnabledSignal.connect(self._currentView.setLineWidgetEnabled)

        self.setDropEnabled(self._dropEnabled)
        self.displayChangedSignal.emit(self._currentView)

    def setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled and self._displayType==self.DISPLAY_SLICEVIEWER:
            self._currentView.setAcceptDrops(True)
            self._currentView.dragEnterEvent = lambda event: event.accept()
            self._currentView.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._currentView.setAcceptDrops(False)

    def setMainImage(self, imageController):
        if hasattr(self._currentView, 'setMainImage'):
            self._currentView.setMainImage(imageController)

    def setSecondaryImage(self, imageController):
        if hasattr(self._currentView, 'setSecondaryImage'):
            self._currentView.setSecondaryImage(imageController)
