import os

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QToolBar, QAction

from GUI.Viewers.sliceViewer import SliceViewerVTK


class ElementToolbar(QToolBar):
    def __init__(self, controller):
        QToolBar.__init__(self)

        self._controller = controller
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

        self._controller.displayChangedSignal.connect(self._handleDisplayChange)

    def _handleButtonDVH(self, pressed):
        if self._buttonDVH.isChecked() != pressed:
            self._buttonDVH.setChecked(pressed)
            return

        if pressed:
            self._controller.setDisplayType(self._controller.DISPLAY_DVH)
            self._handleButtonViewer(False)
            self._handleButtonGraph(False)

    def _handleButtonGraph(self, pressed):
        if self._buttonGraph.isChecked() != pressed:
            self._buttonGraph.setChecked(pressed)
            return

        if pressed:
            self._controller.setDisplayType(self._controller.DISPLAY_PROFILE)
            self._handleButtonViewer(False)
            self._handleButtonDVH(False)

    def _handleButtonViewer(self, pressed):
        if self._buttonViewer.isChecked() != pressed:
            self._buttonViewer.setChecked(pressed)
            return

        if pressed:
            self._controller.setDisplayType(self._controller.DISPLAY_SLICEVIEWER)
            self._handleButtonGraph(False)
            self._handleButtonDVH(False)

    def _handleDisplayChange(self, view):
        if isinstance(view, SliceViewerVTK):
            self._handleButtonViewer(True)
