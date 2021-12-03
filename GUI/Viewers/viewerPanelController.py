from PyQt5.QtCore import QObject, pyqtSignal

from GUI.ViewControllers.gridFourElementController import GridFourElementController
from GUI.Viewers.gridFourElements import GridFourElements


class ViewerPanelController(QObject):
    LAYOUT_FOUR = 'LAYOUT_FOUR'
    viewerGridChangeSignal = pyqtSignal(object)

    def __init__(self, viewController):
        QObject.__init__(self)

        self._dropEnabled = False
        self._independentViewsEnabled = False
        self._gridController = None
        self._layout = self.LAYOUT_FOUR
        self._parent = viewController
        self._view = None

        self.setLayout(self.LAYOUT_FOUR)
        self.setIndependentViewsEnabled(self._independentViewsEnabled)

    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                print(e)
                e.accept()
                self._gridController.setMainImage(self.getSelectedImageController())
                return
        e.ignore()

    def getIndependentViewsEnabled(self):
        return self._independentViewsEnabled

    def getSelectedImageController(self):
        return self._parent.getSelectedImageController()

    def getViewerGrid(self):
        return self._view

    def setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled:
            self._view.setAcceptDrops(True)
            self._view.dragEnterEvent = lambda event: event.accept()
            self._view.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._view.setAcceptDrops(False)

    def setIndependentViewsEnabled(self, enabled):
        self.setDropEnabled(not enabled)
        self._gridController.setIndependentViewsEnabled(enabled)
        self._independentViewsEnabled = enabled

    def setLayout(self, layout):
        self._layout = layout

        if self._layout==self.LAYOUT_FOUR:
            self._gridController = GridFourElementController(self)
            self._view = GridFourElements(self._gridController)

        if self._view==None:
            return

        self.viewerGridChangeSignal.emit(self._view)
