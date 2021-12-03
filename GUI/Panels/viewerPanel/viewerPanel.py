from PyQt5.QtWidgets import QWidget, QVBoxLayout

from GUI.Panels.viewerPanel.ViewerToolbar import ViewerToolbar


class ViewerPanel(QWidget):
    def __init__(self, viewerController):
        QWidget.__init__(self)

        self._layout = QVBoxLayout(self)
        self._toolbar = ViewerToolbar(viewerController)
        self._viewerController = viewerController
        self._viewerWidget = None

        self._layout.addWidget(self._toolbar)
        self.setViewerGrid(self._viewerController.getViewerGrid())

        self._viewerController.viewerGridChangeSignal.connect(self.setViewerGrid)

    def setViewerGrid(self, viewerWidget):
        if not self._viewerWidget is None:
            self._layout.removeWidget(self._viewerWidget)

        self._layout.addWidget(viewerWidget)
        self._viewerWidget = viewerWidget
