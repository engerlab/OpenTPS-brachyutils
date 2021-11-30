from PyQt5 import QtCore
from PyQt5.QtWidgets import QHBoxLayout, QFrame, QSplitter, QWidget, QVBoxLayout

from GUI.Viewers.gridElement import GridElement


class GridFourElements(QWidget):
    def __init__(self, viewerController):
        QWidget.__init__(self)

        self._viewerController = viewerController

        botLeft = QFrame(self)
        botRight = QFrame(self)
        topLeft = QFrame(self)
        topRight = QFrame(self)

        botLeft.setFrameShape(QFrame.StyledPanel)
        botRight.setFrameShape(QFrame.StyledPanel)
        topLeft.setFrameShape(QFrame.StyledPanel)
        topRight.setFrameShape(QFrame.StyledPanel)

        botLeftLayout = QVBoxLayout(botLeft)
        botRightLayout = QVBoxLayout(botRight)
        topLeftLayout = QVBoxLayout(topLeft)
        topRightLayout = QVBoxLayout(topRight)

        botLeftLayout.setContentsMargins(0, 0, 0, 0)
        botRightLayout.setContentsMargins(0, 0, 0, 0)
        topLeftLayout.setContentsMargins(0, 0, 0, 0)
        topRightLayout.setContentsMargins(0, 0, 0, 0)

        botLeftLayout.addWidget(GridElement(self._viewerController.botLeftController))
        botRightLayout.addWidget(GridElement(self._viewerController.botRightController))
        topLeftLayout.addWidget(GridElement(self._viewerController.topLeftController))
        topRightLayout.addWidget(GridElement(self._viewerController.topRightController))


        # Horizontal splitter
        hbox = QHBoxLayout(self)

        left = QFrame(self)
        left.setFrameShape(QFrame.StyledPanel)

        right = QFrame(self)
        right.setFrameShape(QFrame.StyledPanel)

        splitter = QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

        hbox.addWidget(splitter)
        hbox.setContentsMargins(0, 0, 0, 0)


        # Vertical splitters
        vbox = QVBoxLayout(left)
        vbox.setContentsMargins(0, 0, 0, 0)

        leftSplitter = QSplitter(QtCore.Qt.Vertical)
        leftSplitter.addWidget(botLeft)
        leftSplitter.addWidget(topLeft)
        leftSplitter.setStretchFactor(1, 1)
        vbox.addWidget(leftSplitter)

        vbox = QVBoxLayout(right)
        vbox.setContentsMargins(0, 0, 0, 0)

        rightSplitter = QSplitter(QtCore.Qt.Vertical)
        rightSplitter.addWidget(botRight)
        rightSplitter.addWidget(topRight)
        rightSplitter.setStretchFactor(1, 1)
        vbox.addWidget(rightSplitter)
