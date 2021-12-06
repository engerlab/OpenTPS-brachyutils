from PyQt5.QtCore import QObject, pyqtSignal

from GUI.ViewControllers.ViewersControllers.SliceViewerController import SliceViewerController
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
        self._view = None
        self._viewController = None
        self._viewerPanelController = viewerPanelController

        self.setDisplayType(self.DISPLAY_SLICEVIEWER)
        self._viewerPanelController.independentViewsEnabledSignal.connect(self.setDropEnabled)

    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                self._viewController.setMainImage(self.getSelectedImageController())
                return
        e.ignore()

    def getDisplayView(self):
        return self._view

    def getSelectedImageController(self):
        print(self._viewerPanelController.getSelectedImageController().getName())
        return self._viewerPanelController.getSelectedImageController()

    def setDisplayType(self, displayType):
        if displayType==self._displayType:
            return

        self._displayType = displayType

        if self._displayType==self.DISPLAY_DVH:
            self._view = DVHPlot()

        if self._displayType==self.DISPLAY_NONE:
            self._view = BlackEmptyPlot()

        if self._displayType==self.DISPLAY_PROFILE:
            self._view = ProfilePlot()

        if self._displayType==self.DISPLAY_SLICEVIEWER:
            if self._viewController is None:
                self._viewController = SliceViewerController()
            self._view = SliceViewerVTK(self._viewController)

            self._viewerPanelController.crossHairEnabledSignal.connect(self._viewController.setCrossHairEnabled)
            self._viewerPanelController.windowLevelEnabledSignal.connect(self._viewController.setWindowLevelEnabled)

        self.setDropEnabled(self._dropEnabled)
        self.displayChangedSignal.emit(self._view)

    def setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled and self._displayType==self.DISPLAY_SLICEVIEWER:
            self._view.setAcceptDrops(True)
            self._view.dragEnterEvent = lambda event: event.accept()
            self._view.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._view.setAcceptDrops(False)

    def setMainImage(self, imageController):
        self._viewController.setMainImage(imageController)

    def setSecondaryImage(self, imageController):
        self._viewController.setSecondaryImage(imageController)
