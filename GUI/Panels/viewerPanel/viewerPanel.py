
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from GUI.Panels.viewerPanel.gridFourElements import GridFourElements
from GUI.Panels.viewerPanel.viewerToolbar import ViewerToolbar


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

        self.setToolbar(self._viewToolbar)
        self.setLayout(self.LAYOUT_FOUR)
        if self._layoutType == 'LAYOUT_FOUR':
            self._viewController.numberOfViewerPanelElement = 4

        self._viewController.independentViewsEnabledSignal.connect(lambda enabled: self.setDropEnabled(not enabled))
        self.setDropEnabled(not self._viewController.getIndependentViewsEnabled())

    def _dropEvent(self, e):
        if e.mimeData().hasText():
            if (e.mimeData().text() == 'image'):
                e.accept()
                self._viewController.setMainImage(self._viewController.getSelectedImageController())
                return
        e.ignore()

    def setDropEnabled(self, enabled):
        self._dropEnabled = enabled

        if enabled:
            self._viewerGrid.setAcceptDrops(True)
            self._viewerGrid.dragEnterEvent = lambda event: event.accept()
            self._viewerGrid.dropEvent = lambda event: self._dropEvent(event)
        else:
            self._viewerGrid.setAcceptDrops(False)

    def setLayout(self, layoutType):
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

    def setToolbar(self, toolbar):
        #TODO: remove toolbar if already existing add add newToolabr above
        self._toolbar = toolbar
        self._layout.addWidget(self._toolbar)
