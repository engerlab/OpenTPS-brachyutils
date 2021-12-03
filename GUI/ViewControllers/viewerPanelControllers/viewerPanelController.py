from PyQt5.QtCore import QObject, pyqtSignal

from GUI.ViewControllers.viewerPanelControllers.gridFourElementController import GridFourElementController
from GUI.Panels.viewerPanel.gridFourElements import GridFourElements


class ViewerPanelController(QObject):
    LAYOUT_FOUR = 'LAYOUT_FOUR'

    independentViewsEnabledSignal = pyqtSignal(bool)
    viewerGridChangeSignal = pyqtSignal(object)

    def __init__(self, viewController):
        QObject.__init__(self)

        self._dropEnabled = False
        self._independentViewsEnabled = None
        self._gridController = None
        self._layout = self.LAYOUT_FOUR
        self._parent = viewController
        self._view = None

        self.setLayout(self.LAYOUT_FOUR)
        self.setIndependentViewsEnabled(False)

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
        if enabled==self._independentViewsEnabled:
            return

        self.setDropEnabled(not enabled)
        self._independentViewsEnabled = enabled

        self.independentViewsEnabledSignal.emit(self._independentViewsEnabled)

    def setLayout(self, layout):
        self._layout = layout

        if not self._gridController is None:
            self.independentViewsEnabledSignal.disconnect(self._gridController.setIndependentViewsEnabled)

        if self._layout==self.LAYOUT_FOUR:
            self._gridController = GridFourElementController(self)
            self._view = GridFourElements(self._gridController)

            self._gridController.setIndependentViewsEnabled(self._independentViewsEnabled)
            self.independentViewsEnabledSignal.connect(self._gridController.setIndependentViewsEnabled)

        if self._view==None:
            return

        self.viewerGridChangeSignal.emit(self._view)
