from PyQt5.QtCore import QObject, pyqtSignal

from GUI.Panels.viewerPanel.viewerToolbar import ViewerToolbar
from GUI.ViewControllers.viewerPanelControllers.gridFourElementController import GridFourElementController
from GUI.Panels.viewerPanel.gridFourElements import GridFourElements


class ViewerPanelController(QObject):
    LAYOUT_FOUR = 'LAYOUT_FOUR'

    crossHairEnabledSignal = pyqtSignal(bool)
    independentViewsEnabledSignal = pyqtSignal(bool)
    lineWidgetEnabledSignal = pyqtSignal(object)
    windowLevelEnabledSignal = pyqtSignal(bool)

    def __init__(self, viewerPanel, viewController):
        QObject.__init__(self)

        self._crossHairEnabled = None
        self._dropEnabled = False
        self._independentViewsEnabled = True
        self._windowLevelEnabled = None
        self._gridController = None
        self._layout = self.LAYOUT_FOUR
        self._view = viewerPanel
        self._viewerGrid = None
        self._viewToolbar = ViewerToolbar(self)
        self._viewController = viewController

        self._view.setToolbar(self._viewToolbar)
        self.setLayout(self.LAYOUT_FOUR)
        self.setIndependentViewsEnabled(False)  # must be called after layout is set
        self.setCrossHairEnabled(False)
        self.setWindowLevelEnabled(False)


    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                self._gridController.setMainImage(self.getSelectedImageController())
                return
        e.ignore()

    def getIndependentViewsEnabled(self):
        return self._independentViewsEnabled

    def getSelectedImageController(self):
        return self._viewController.getSelectedImageController()

    def getViewerGrid(self):
        return self._viewerGrid

    def setCrossHairEnabled(self, enabled):
        if enabled==self._crossHairEnabled:
            return

        if self._windowLevelEnabled and enabled:
            self.setWindowLevelEnabled(False)

        self._crossHairEnabled = enabled
        self.crossHairEnabledSignal.emit(self._crossHairEnabled)

    def setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled:
            self._viewerGrid.setAcceptDrops(True)
            self._viewerGrid.dragEnterEvent = lambda event: event.accept()
            self._viewerGrid.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._viewerGrid.setAcceptDrops(False)

    def setIndependentViewsEnabled(self, enabled):
        if enabled==self._independentViewsEnabled:
            return

        self.setDropEnabled(not enabled)
        self._independentViewsEnabled = enabled

        self.independentViewsEnabledSignal.emit(self._independentViewsEnabled)

    def setLineWidgetEnabled(self, callback):
        self.lineWidgetEnabledSignal.emit(callback)

    def setWindowLevelEnabled(self, enabled):
        if enabled==self._windowLevelEnabled:
            return

        if self._crossHairEnabled and enabled:
            self.setCrossHairEnabled(False)

        self._windowLevelEnabled = enabled
        self.windowLevelEnabledSignal.emit(self._windowLevelEnabled)

    def setLayout(self, layout):
        self._layout = layout

        if not self._gridController is None:
            self.independentViewsEnabledSignal.disconnect(self._gridController.setIndependentViewsEnabled)

        if self._layout==self.LAYOUT_FOUR:
            self._viewerGrid = GridFourElements()
            self._gridController = GridFourElementController(self._viewerGrid, self)


        if self._viewerGrid==None:
            return

        self._view.setWidget(self._viewerGrid)

        if self._layout == self.LAYOUT_FOUR:
            self._viewerGrid.setEqualSize()

    def setMainImage(self, imageController):
        self._viewController.setMainImage(imageController)
