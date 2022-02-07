import os

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction

from Core.event import Event
import GUI.Viewer.dataViewer as dataViewer


class DataViewerToolbar(QToolBar):
    def __init__(self):
        QToolBar.__init__(self)

        # Events
        self.displayTypeSignal = Event(object)

        self.setIconSize(QSize(16, 16))

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        self._buttonDVH = QAction(QIcon(iconPath + "equalizer.png"), "DVH", self)
        self._buttonDVH.setStatusTip("DVH")
        self._buttonDVH.triggered.connect(self._handleButtonDVH)
        self._buttonDVH.setCheckable(True)

        self._buttonProfile = QAction(QIcon(iconPath + "chart.png"), "Graph", self)
        self._buttonProfile.setStatusTip("Graph")
        self._buttonProfile.triggered.connect(self._handleButtonGraph)
        self._buttonProfile.setCheckable(True)

        self._buttonViewer = QAction(QIcon(iconPath + "x-ray.png"), "Image viewer", self)
        self._buttonViewer.setStatusTip("Image viewer")
        self._buttonViewer.triggered.connect(self._handleButtonViewer)
        self._buttonViewer.setCheckable(True)

        self.addAction(self._buttonViewer)
        self.addAction(self._buttonProfile)
        self.addAction(self._buttonDVH)

        self.addSeparator()

    def _handleButtonDVH(self, pressed):
        if self._buttonDVH.isChecked() != pressed:
            self._buttonDVH.setChecked(pressed)
            return

        if pressed:
            self.displayTypeSignal.emit(dataViewer.DataViewer.DisplayTypes.DISPLAY_DVH)
            self._handleButtonViewer(False)
            self._handleButtonGraph(False)

    def _handleButtonGraph(self, pressed):
        if self._buttonProfile.isChecked() != pressed:
            self._buttonProfile.setChecked(pressed)
            return

        if pressed:
            self.displayTypeSignal.emit(dataViewer.DataViewer.DisplayTypes.DISPLAY_PROFILE)
            self._handleButtonViewer(False)
            self._handleButtonDVH(False)

    def _handleButtonViewer(self, pressed):
        if self._buttonViewer.isChecked() != pressed:
            self._buttonViewer.setChecked(pressed)
            return

        if pressed:
            self.displayTypeSignal.emit(dataViewer.DataViewer.DisplayTypes.DISPLAY_IMAGE)
            self._handleButtonGraph(False)
            self._handleButtonDVH(False)

    def setViewerType(self, viewerType):
        if viewerType==dataViewer.DataViewer.DisplayTypes.DISPLAY_IMAGE:
            self._buttonViewer.setChecked(True)
