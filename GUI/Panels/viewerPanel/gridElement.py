from PyQt5.QtWidgets import QWidget, QVBoxLayout

from GUI.Panels.viewerPanel.gridElementToolbar import ElementToolbar


class GridElement(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._mainLayout = QVBoxLayout(self)
        self._toolbar = ElementToolbar(viewController)
        self._viewController = viewController
        self._viewerWidget = None

        self._mainLayout.addWidget(self._toolbar)
        self.setLayout(self._mainLayout)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        if not self._viewController.getDisplayView() is None:
            self.setDisplayWidget(self._viewController.getDisplayView())

        self._viewController.displayChangedSignal.connect(self.setDisplayWidget)

    def setDisplayWidget(self, viewerWidget):
        if not (self._viewerWidget is None):
            self._mainLayout.removeWidget(self._viewerWidget)

        self._viewerWidget = viewerWidget
        self._mainLayout.addWidget(self._viewerWidget)
        self._viewerWidget.show()



