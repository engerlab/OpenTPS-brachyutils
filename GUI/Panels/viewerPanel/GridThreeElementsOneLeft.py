from PyQt5 import QtCore
from PyQt5.QtWidgets import QHBoxLayout, QFrame, QSplitter, QWidget, QVBoxLayout

from GUI.Panels.viewerPanel.gridElement import GridElement


class GridThreeElementsOneLeft(QWidget):
    def __init__(self, viewerController):
        QWidget.__init__(self)

        self._viewerController = viewerController

        botRight = QFrame(self)
        left = QFrame(self)
        topRight = QFrame(self)

        botRight.setFrameShape(QFrame.StyledPanel)
        left.setFrameShape(QFrame.StyledPanel)
        topRight.setFrameShape(QFrame.StyledPanel)

        botRightLayout = QVBoxLayout(botRight)
        leftLayout = QVBoxLayout(left)
        topRightLayout = QVBoxLayout(topRight)

        botRightLayout.setContentsMargins(0, 0, 0, 0)
        leftLayout.setContentsMargins(0, 0, 0, 0)
        topRightLayout.setContentsMargins(0, 0, 0, 0)

        botRightLayout.addWidget(GridElement(self._viewerController.controller0))
        leftLayout.addWidget(GridElement(self._viewerController.controller1))
        topRightLayout.addWidget(GridElement(self._viewerController.controller2))


        # Horizontal splitter
        hbox = QHBoxLayout(self)

        right = QFrame(self)
        right.setFrameShape(QFrame.StyledPanel)

        splitter = QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

        hbox.addWidget(splitter)
        hbox.setContentsMargins(0, 0, 0, 0)


        # Vertical splitter
        vbox = QVBoxLayout(right)
        vbox.setContentsMargins(0, 0, 0, 0)

        rightSplitter = QSplitter(QtCore.Qt.Vertical)
        rightSplitter.addWidget(botRight)
        rightSplitter.addWidget(topRight)
        rightSplitter.setStretchFactor(1, 1)
        vbox.addWidget(rightSplitter)
