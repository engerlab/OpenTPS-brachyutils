import os

from PyQt5.QtCore import QSize, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction

import GUI.Viewer.dataViewer as gridElement
from Core.event import Event
from GUI.Viewer.Viewers.sliceViewer import SliceViewerVTK


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

        self._buttonGraph = QAction(QIcon(iconPath + "chart.png"), "Graph", self)
        self._buttonGraph.setStatusTip("Graph")
        self._buttonGraph.triggered.connect(self._handleButtonGraph)
        self._buttonGraph.setCheckable(True)

        self._buttonViewer = QAction(QIcon(iconPath + "x-ray.png"), "Image viewer", self)
        self._buttonViewer.setStatusTip("Image viewer")
        self._buttonViewer.triggered.connect(self._handleButtonViewer)
        self._buttonViewer.setCheckable(True)

        self.addAction(self._buttonViewer)
        self.addAction(self._buttonGraph)
        self.addAction(self._buttonDVH)

    def _handleButtonDVH(self, pressed):
        if self._buttonDVH.isChecked() != pressed:
            self._buttonDVH.setChecked(pressed)
            return

        if pressed:
            self.displayTypeSignal.emit(gridElement.DataViewer.DISPLAY_DVH)
            self._handleButtonViewer(False)
            self._handleButtonGraph(False)

    def _handleButtonGraph(self, pressed):
        if self._buttonGraph.isChecked() != pressed:
            self._buttonGraph.setChecked(pressed)
            return

        if pressed:
            self.displayTypeSignal.emit(gridElement.DataViewer.DISPLAY_PROFILE)
            self._handleButtonViewer(False)
            self._handleButtonDVH(False)

    def _handleButtonViewer(self, pressed):
        if self._buttonViewer.isChecked() != pressed:
            self._buttonViewer.setChecked(pressed)
            return

        if pressed:
            self.displayTypeSignal.emit(gridElement.DataViewer.DISPLAY_SLICEVIEWER)
            self._handleButtonGraph(False)
            self._handleButtonDVH(False)

    def handleDisplayChange(self, view):
        if isinstance(view, SliceViewerVTK):
            self._handleButtonViewer(True)
