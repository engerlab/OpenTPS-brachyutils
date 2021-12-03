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

        self._buttonViewer = QAction(QIcon(iconPath+"x-ray.png"), "Image viewer", self)
        self._buttonViewer.setStatusTip("Image viewer")
        self._buttonViewer.triggered.connect(self._handleButtonViewer)
        self._buttonViewer.setCheckable(True)

        self._buttonGraph = QAction(QIcon(iconPath + "chart.png"), "Graph", self)
        self._buttonGraph.setStatusTip("Graph")
        self._buttonGraph.triggered.connect(self._handleButtonGraph)
        self._buttonGraph.setCheckable(True)

        self.addAction(self._buttonViewer)
        self.addAction(self._buttonGraph)

        self._controller.displayChangeSignal.connect(self._handleDisplayChange)

    def _handleButtonViewer(self, pressed):
        if self._buttonViewer.isChecked() != pressed:
            self._buttonViewer.setChecked(pressed)
            return

        if pressed:
            self._controller.setDisplayType(self._controller.DISPLAY_SLICEVIEWER)
            self._handleButtonGraph(False)

    def _handleButtonGraph(self, pressed):
        if self._buttonGraph.isChecked() != pressed:
            self._buttonGraph.setChecked(pressed)
            return

        if pressed:
            self._controller.setDisplayType(self._controller.DISPLAY_GRAPH)
            self._handleButtonViewer(False)

    def _handleDisplayChange(self, view):
        if isinstance(view, SliceViewerVTK):
            self._handleButtonViewer(True)
