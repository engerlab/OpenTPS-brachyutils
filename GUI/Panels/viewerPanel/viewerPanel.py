from PyQt5.QtWidgets import QWidget, QVBoxLayout

from GUI.Panels.viewerPanel.viewerToolbar import ViewerToolbar


class ViewerPanel(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self._layout = QVBoxLayout(self)
        self._viewerWidget = None

    def setToolbar(self, toolbar):
        self._toolbar = toolbar
        self._layout.addWidget(self._toolbar)

    def setWidget(self, viewerWidget):
        if not self._viewerWidget is None:
            self._layout.removeWidget(self._viewerWidget)

        self._layout.addWidget(viewerWidget)
        self._viewerWidget = viewerWidget
