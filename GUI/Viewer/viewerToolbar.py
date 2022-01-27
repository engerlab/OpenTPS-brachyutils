import os

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction
from Core.event import Event


class ViewerToolbar(QToolBar):

    PLAY_STATUS = 1
    PAUSE_STATUS = 0

    def __init__(self, viewController):
        QToolBar.__init__(self)

        self._viewController = viewController
        self.setIconSize(QSize(16, 16))

        self.iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        self._buttonOpen = QAction(QIcon(self.iconPath + "folder-open.png"), "Open files or folder", self)

        self._buttonChain = QAction(QIcon(self.iconPath+"chain-unchain.png"), "Independent views", self)
        self._buttonChain.setStatusTip("Independent views")
        self._buttonChain.triggered.connect(self._handleButtonChain)
        self._buttonChain.setCheckable(True)
        self._buttonChain.setChecked(self._viewController.independentViewsEnabled)

        self._buttonContrast = QAction(QIcon(self.iconPath + "contrast.png"), "Window level", self)
        self._buttonContrast.setStatusTip("Window level")
        self._buttonContrast.triggered.connect(self._handleWindowLevel)
        self._buttonContrast.setCheckable(True)

        self._buttonCrossHair = QAction(QIcon(self.iconPath + "geolocation.png"), "Crosshair", self)
        self._buttonCrossHair.setStatusTip("Crosshair")
        self._buttonCrossHair.triggered.connect(self._handleCrossHair)
        self._buttonCrossHair.setCheckable(True)

        self.addAction(self._buttonOpen)
        self.addAction(self._buttonChain)
        self.addAction(self._buttonCrossHair)
        self.addAction(self._buttonContrast)

        self.addSeparator()

        ## dynamic options buttons
        self._buttonFaster = QAction(QIcon(self.iconPath + "fast.png"), "Speed", self)
        self._buttonFaster.setStatusTip("Speed up the dynamic viewers evolution")
        self._buttonFaster.triggered.connect(self._handleFaster)

        self._buttonSlower = QAction(QIcon(self.iconPath + "slow.png"), "Speed", self)
        self._buttonSlower.setStatusTip("Slows the dynamic viewers evolution")
        self._buttonSlower.triggered.connect(self._handleSlower)

        self._buttonPlayPause = QAction(QIcon(self.iconPath + "play.png"), "Speed", self)
        self._buttonPlayPause.setStatusTip("Classical Play Pause of course")
        self._buttonPlayPause.triggered.connect(self._handlePlayPause)
        self.playPauseStatus = self.PLAY_STATUS

        self._buttonRefreshRate = QAction('RR', self)
        self._buttonRefreshRate.setStatusTip("Change the refresh rate of the dynamic viewers")
        self._buttonRefreshRate.triggered.connect(self._handleRefreshRate)

        self.fasterSignal = Event()
        self.slowerSignal = Event()
        self.playPauseSignal = Event(bool)
        self.refreshRateChangedSignal = Event(int)
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

        self.addAction(self._buttonSlower)
        self.addAction(self._buttonPlayPause)
        self._buttonPlayPause.setIcon(QIcon(self.iconPath + "pause.jpg"))
        self.addAction(self._buttonFaster)
        self.addAction(self._buttonRefreshRate)

    def removeDynamicButtons(self):

        self.removeAction(self._buttonSlower)
        self.removeAction(self._buttonPlayPause)
        self.removeAction(self._buttonFaster)
        self.removeAction(self._buttonRefreshRate)

    def _handleFaster(self):
        self.fasterSignal.emit()


    def _handleSlower(self):
        self.slowerSignal.emit()


    def _handlePlayPause(self):
        self.playPauseStatus = not self.playPauseStatus

        if self.playPauseStatus:
            self._buttonPlayPause.setIcon(QIcon(self.iconPath + "pause.jpg"))
        elif not self.playPauseStatus:
            self._buttonPlayPause.setIcon(QIcon(self.iconPath + "play.png"))

        self.playPauseSignal.emit(self.playPauseStatus)


    def _handleRefreshRate(self):
        return 0

