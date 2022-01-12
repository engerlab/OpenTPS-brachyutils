
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from GUI.Viewer.gridFourElements import GridFourElements
from GUI.Viewer.viewerToolbar import ViewerToolbar


class ViewerPanel(QWidget):
    LAYOUT_FOUR = 'LAYOUT_FOUR'

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._dropEnabled = False
        self._layout = QVBoxLayout(self)
        self._layoutType = None
        self._viewerGrid = None
        self._viewToolbar = ViewerToolbar(viewController)
        self._viewController = viewController

        self._setToolbar(self._viewToolbar)
        self._setLayout(self.LAYOUT_FOUR)
        if self._layoutType == 'LAYOUT_FOUR':
            self._viewController.numberOfViewerPanelElement = 4

        self._viewController.independentViewsEnabledSignal.connect(lambda enabled: self._setDropEnabled(not enabled))
        self._setDropEnabled(not self._viewController.independentViewsEnabled)

    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                self._viewController.mainImage = self._viewController.selectedImage
                return
        e.ignore()

    def _setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled:
            self._viewerGrid.setAcceptDrops(True)
            self._viewerGrid.dragEnterEvent = lambda event: event.accept()
            self._viewerGrid.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._viewerGrid.setAcceptDrops(False)

    def _setLayout(self, layoutType):
        self._layoutType = layoutType

        if not self._viewerGrid is None:
            self._layoutType.removeWidget(self._viewerGrid)

        if self._layoutType == self.LAYOUT_FOUR:
            self._viewerGrid = GridFourElements(self._viewController)

        if self._viewerGrid==None:
            return

        self._layout.addWidget(self._viewerGrid)

        if self._layoutType == self.LAYOUT_FOUR:
            self._viewerGrid.setEqualSize()

    def _setToolbar(self, toolbar):
        #TODO: remove toolbar if already existing add add newToolabr above
        self._toolbar = toolbar
        self._layout.addWidget(self._toolbar)
