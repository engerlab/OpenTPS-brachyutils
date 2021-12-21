from PyQt5.QtWidgets import QWidget, QVBoxLayout

from GUI.Panels.viewerPanel.gridElementToolbar import ElementToolbar


class GridElement(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self._mainLayout = QVBoxLayout(self)
        self._toolbar = None
        self._viewerWidget = None

        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

    def setToolbar(self, toolbar):
        self._toolbar = toolbar
        self._mainLayout.addWidget(self._toolbar)

    def setDisplayWidget(self, viewerWidget):
        if not (self._viewerWidget is None):
            self._mainLayout.removeWidget(self._viewerWidget)

        self._viewerWidget = viewerWidget
        self._mainLayout.addWidget(self._viewerWidget)
        self._viewerWidget.show()



