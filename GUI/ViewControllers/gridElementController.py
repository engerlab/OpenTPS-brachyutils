from PyQt5.QtCore import QObject, pyqtSignal

from GUI.ViewControllers.SliceViewerController import SliceViewerController
from GUI.Viewers.sliceViewer import SliceViewerVTK


class GridElementController(QObject):
    DISPLAY_DVH = 'DVH'
    DISPLAY_SLICEVIEWER = 'SLICE'

    displayChangeSignal = pyqtSignal(object)

    def __init__(self, parent=None):
        QObject.__init__(self)

        self._displayType = None
        self._dropEnabled = False
        self._parent = parent
        self._viewController = None
        self._view = None

        self.setDisplayType(self.DISPLAY_SLICEVIEWER)

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
        return self._parent.getSelectedImageController()

    def setDisplayType(self, displayType):
        self._displayType = displayType

        if self._displayType==self.DISPLAY_SLICEVIEWER:
            self._viewController = SliceViewerController()
            self._view = SliceViewerVTK(self._viewController)

            self.setDropEnabled(self._dropEnabled)

            self.displayChangeSignal.emit(self._view)

    def setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled:
            self._view.setAcceptDrops(True)
            self._view.dragEnterEvent = lambda event: event.accept()
            self._view.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._view.setAcceptDrops(False)

    def setMainImage(self, imageController):
        self._viewController.setMainImage(imageController)

    def setSecondaryImage(self, imageController):
        self._viewController.setSecondaryImage(imageController)
