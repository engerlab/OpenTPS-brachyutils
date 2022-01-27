import os

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction


class ViewerToolbar(QToolBar):
    def __init__(self, viewController):
        QToolBar.__init__(self)

        self._viewController = viewController
        self.setIconSize(QSize(16, 16))

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        self._buttonOpen = QAction(QIcon(iconPath + "folder-open.png"), "Open files or folder", self)

        self._buttonChain = QAction(QIcon(iconPath+"chain-unchain.png"), "Independent views", self)
        self._buttonChain.setStatusTip("Independent views")
        self._buttonChain.triggered.connect(self._handleButtonChain)
        self._buttonChain.setCheckable(True)
        self._buttonChain.setChecked(self._viewController.independentViewsEnabled)

        self._buttonContrast = QAction(QIcon(iconPath + "contrast.png"), "Window level", self)
        self._buttonContrast.setStatusTip("Window level")
        self._buttonContrast.triggered.connect(self._handleWindowLevel)
        self._buttonContrast.setCheckable(True)

        self._buttonCrossHair = QAction(QIcon(iconPath + "geolocation.png"), "Crosshair", self)
        self._buttonCrossHair.setStatusTip("Crosshair")
        self._buttonCrossHair.triggered.connect(self._handleCrossHair)
        self._buttonCrossHair.setCheckable(True)

        self.addAction(self._buttonOpen)
        self.addAction(self._buttonChain)
        self.addAction(self._buttonCrossHair)
        self.addAction(self._buttonContrast)

        self.addSeparator()

        ## dynamic options buttons
        self._buttonFaster = QAction(QIcon(iconPath + "fast.png"), "Speed", self)
        self._buttonFaster.setStatusTip("Speed up the dynamic viewers evolution")
        self._buttonFaster.triggered.connect(self._handleFaster)

        self._buttonSlower = QAction(QIcon(iconPath + "slow.png"), "Speed", self)
        self._buttonSlower.setStatusTip("Slows the dynamic viewers evolution")
        self._buttonSlower.triggered.connect(self._handleSlower)

        self._buttonPlayPause = QAction(QIcon(iconPath + "pause.png"), "Speed", self)
        self._buttonPlayPause.setStatusTip("Classical Play Pause of course")
        self._buttonPlayPause.triggered.connect(self._handlePlayPause)

        self._buttonRefreshRate = QAction('RR', self)
        self._buttonRefreshRate.setStatusTip("Change the refresh rate of the dynamic viewers")
        self._buttonRefreshRate.triggered.connect(self._handleRefreshRate)


        # self.addDynamicButtons()

        self._viewController.independentViewsEnabledSignal.connect(self._handleButtonChain)
        self._viewController.windowLevelEnabledSignal.connect(self._handleWindowLevel)
        self._viewController.crossHairEnabledSignal.connect(self._handleCrossHair)

    def _handleButtonChain(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonChain.isChecked() != pressed:
            self._buttonChain.setChecked(pressed)
            return

        self._viewController.independentViewsEnabled = pressed

    def _handleCrossHair(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonCrossHair.isChecked() != pressed:
            self._buttonCrossHair.setChecked(pressed)
            return

        self._viewController.crossHairEnabled = pressed

    def _handleWindowLevel(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonContrast.isChecked() != pressed:
            self._buttonContrast.setChecked(pressed)
            return

        self._viewController.windowLevelEnabled = pressed

    def addDynamicButtons(self):
        print('dynamic buttons added')

        self.addAction(self._buttonSlower)
        self.addAction(self._buttonPlayPause)
        self.addAction(self._buttonFaster)
        self.addAction(self._buttonRefreshRate)

    def removeDynamicButtons(self):
        print('dynamic buttons removed')
        self.removeAction(self._buttonSlower)
        self.removeAction(self._buttonPlayPause)
        self.removeAction(self._buttonFaster)
        self.removeAction(self._buttonRefreshRate)

    def _handleFaster(self, pressed):
        # if self._buttonChain.isChecked() != pressed:
        #     self._buttonChain.setChecked(pressed)
        #     return
        #
        # self._viewController.independentViewsEnabled = pressed
        return 0

    def _handleSlower(self, pressed):
        return 0

    def _handlePlayPause(self, pressed):
        return 0

    def _handleRefreshRate(self, pressed):
        return 0

