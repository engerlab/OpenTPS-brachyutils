import os

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction, QDialog, QPushButton, QLineEdit, QScrollBar, QVBoxLayout
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

        self._buttonIndependentViews = QAction(QIcon(self.iconPath + "chain-unchain.png"), "Independent views", self)
        self._buttonIndependentViews.setStatusTip("Independent views")
        self._buttonIndependentViews.triggered.connect(self._handleButtonChain)
        self._buttonIndependentViews.setCheckable(True)
        self._buttonIndependentViews.setChecked(self._viewController.independentViewsEnabled)

        self._buttonWindowLevel = QAction(QIcon(self.iconPath + "contrast.png"), "Window level", self)
        self._buttonWindowLevel.setStatusTip("Window level")
        self._buttonWindowLevel.triggered.connect(self._handleWindowLevel)
        self._buttonWindowLevel.setCheckable(True)

        self._buttonCrossHair = QAction(QIcon(self.iconPath + "geolocation.png"), "Crosshair", self)
        self._buttonCrossHair.setStatusTip("Crosshair")
        self._buttonCrossHair.triggered.connect(self._handleCrossHair)
        self._buttonCrossHair.setCheckable(True)

        self.addAction(self._buttonOpen)
        self.addAction(self._buttonIndependentViews)
        self.addAction(self._buttonCrossHair)
        self.addAction(self._buttonWindowLevel)

        self.addSeparator()

        ## dynamic options buttons
        self._buttonFaster = QAction(QIcon(self.iconPath + "fast.png"), "Faster", self)
        self._buttonFaster.setStatusTip("Speed up the dynamic viewers evolution")
        self._buttonFaster.triggered.connect(self._handleFaster)

        self._buttonSlower = QAction(QIcon(self.iconPath + "slow.png"), "Slower", self)
        self._buttonSlower.setStatusTip("Slows the dynamic viewers evolution")
        self._buttonSlower.triggered.connect(self._handleSlower)

        self._buttonPlayPause = QAction(QIcon(self.iconPath + "play.png"), "Play/Pause", self)
        self._buttonPlayPause.setStatusTip("Classical Play Pause of course")
        self._buttonPlayPause.triggered.connect(self._handlePlayPause)
        self.playPauseStatus = self.PLAY_STATUS

        self._buttonRefreshRate = QAction('RR', self)
        self._buttonRefreshRate.setStatusTip("Change the refresh rate of the dynamic viewers")
        self._buttonRefreshRate.triggered.connect(self._handleRefreshRate)

        self.fasterSignal = Event()
        self.slowerSignal = Event()
        self.playPauseSignal = Event(bool)
        self.refreshRateChangedSignal = Event(float)
        self.refreshRateValue = 24
        # self.addDynamicButtons()

        self._viewController.independentViewsEnabledSignal.connect(self._handleButtonChain)
        self._viewController.windowLevelEnabledSignal.connect(self._handleWindowLevel)
        self._viewController.crossHairEnabledSignal.connect(self._handleCrossHair)

    def _handleButtonChain(self, pressed):
        # This is useful if controller emit a signal:
        if self._buttonIndependentViews.isChecked() != pressed:
            self._buttonIndependentViews.setChecked(pressed)
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
        if self._buttonWindowLevel.isChecked() != pressed:
            self._buttonWindowLevel.setChecked(pressed)
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

        refreshRateDialog = RefreshRateDialog(self.refreshRateValue)

        if (refreshRateDialog.exec()):
            self.refreshRateValue = float(refreshRateDialog.rRValueLine.text())
            self.refreshRateChangedSignal.emit(self.refreshRateValue)


class RefreshRateDialog(QDialog):

    def __init__(self, refreshRateValue):
        QDialog.__init__(self)

        self.RRVal = refreshRateValue

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # self.slider = QScrollBar(self)   ## to select the refresh rate with a scroll bar, not used for now
        # self.slider.setOrientation(Qt.Horizontal)
        # self.slider.sliderMoved.connect(self.sliderval)
        # self.main_layout.addWidget(self.slider)

        self.rRValueLine = QLineEdit(str(self.RRVal))
        self.main_layout.addWidget(self.rRValueLine)

        okButton = QPushButton("ok", self)
        okButton.clicked.connect(self.accept)
        self.main_layout.addWidget(okButton)


    def sliderval(self):
        # getting current position of the slider
        value = self.slider.sliderPosition()
