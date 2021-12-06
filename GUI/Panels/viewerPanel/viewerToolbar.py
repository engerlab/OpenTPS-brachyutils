import os

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction


class ViewerToolbar(QToolBar):
    def __init__(self, controller):
        QToolBar.__init__(self)

        self._controller = controller
        self.setIconSize(QSize(16, 16))

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        self._buttonChain = QAction(QIcon(iconPath+"chain-unchain.png"), "Independent views", self)
        self._buttonChain.setStatusTip("Independent views")
        self._buttonChain.triggered.connect(self._handleButtonChain)
        self._buttonChain.setCheckable(True)
        self._buttonChain.setChecked(self._controller.getIndependentViewsEnabled())

        self._buttonContrast = QAction(QIcon(iconPath + "contrast.png"), "Window level", self)
        self._buttonContrast.setStatusTip("Window level")
        self._buttonContrast.triggered.connect(self._handleWindowLevel)
        self._buttonContrast.setCheckable(True)

        self._buttonCrossHair = QAction(QIcon(iconPath + "geolocation.png"), "Crosshair", self)
        self._buttonCrossHair.setStatusTip("Crosshair")
        self._buttonCrossHair.triggered.connect(self._handleCrossHair)
        self._buttonCrossHair.setCheckable(True)

        self._buttonOpen = QAction(QIcon(iconPath + "folder-open.png"), "Open files or folder", self)

        self.addAction(self._buttonOpen)
        self.addAction(self._buttonChain)
        self.addAction(self._buttonCrossHair)
        self.addAction(self._buttonContrast)

        self._controller.independentViewsEnabledSignal.connect(self._handleButtonChain)
        self._controller.windowLevelEnabledSignal.connect(self._handleWindowLevel)
        self._controller.crossHairEnabledSignal.connect(self._handleCrossHair)

    def _handleButtonChain(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonChain.isChecked() != pressed:
            self._buttonChain.setChecked(pressed)
            return

        self._controller.setIndependentViewsEnabled(pressed)

    def _handleCrossHair(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonCrossHair.isChecked() != pressed:
            self._buttonCrossHair.setChecked(pressed)
            return

        self._controller.setCrossHairEnabled(pressed)

    def _handleWindowLevel(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonContrast.isChecked() != pressed:
            self._buttonContrast.setChecked(pressed)
            return

        self._controller.setWindowLevelEnabled(pressed)
