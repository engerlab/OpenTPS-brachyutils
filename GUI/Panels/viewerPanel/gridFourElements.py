from PyQt5 import QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QHBoxLayout, QFrame, QSplitter, QWidget, QVBoxLayout

from GUI.Panels.viewerPanel.gridElement import GridElement


class GridFourElements(QWidget):
    def __init__(self, viewerController):
        QWidget.__init__(self)

        self._viewerController = viewerController
        self._setEqualSize = False #Use to set equal size before qwidget is effectively shown

        self._botLeft = QFrame(self)
        self._botRight = QFrame(self)
        self._topLeft = QFrame(self)
        self._topRight = QFrame(self)

        self._botLeft.setFrameShape(QFrame.StyledPanel)
        self._botRight.setFrameShape(QFrame.StyledPanel)
        self._topLeft.setFrameShape(QFrame.StyledPanel)
        self._topRight.setFrameShape(QFrame.StyledPanel)

        botLeftLayout = QVBoxLayout(self._botLeft)
        botRightLayout = QVBoxLayout(self._botRight)
        topLeftLayout = QVBoxLayout(self._topLeft)
        topRightLayout = QVBoxLayout(self._topRight)

        botLeftLayout.setContentsMargins(0, 0, 0, 0)
        botRightLayout.setContentsMargins(0, 0, 0, 0)
        topLeftLayout.setContentsMargins(0, 0, 0, 0)
        topRightLayout.setContentsMargins(0, 0, 0, 0)

        botLeftLayout.addWidget(GridElement(self._viewerController.controller0))
        botRightLayout.addWidget(GridElement(self._viewerController.controller1))
        topLeftLayout.addWidget(GridElement(self._viewerController.controller2))
        topRightLayout.addWidget(GridElement(self._viewerController.controller3))


        # Horizontal splitter
        hbox = QHBoxLayout(self)

        self._left = QFrame(self)
        self._left.setFrameShape(QFrame.StyledPanel)

        self._right = QFrame(self)
        self._right.setFrameShape(QFrame.StyledPanel)

        self._horizontalSplitter = QSplitter(QtCore.Qt.Horizontal)
        self._horizontalSplitter.addWidget(self._left)
        self._horizontalSplitter.addWidget(self._right)
        self._horizontalSplitter.setStretchFactor(1, 1)

        hbox.addWidget(self._horizontalSplitter)
        hbox.setContentsMargins(0, 0, 0, 0)


        # Vertical splitters
        vbox = QVBoxLayout(self._left)
        vbox.setContentsMargins(0, 0, 0, 0)

        leftSplitter = QSplitter(QtCore.Qt.Vertical)
        leftSplitter.addWidget(self._botLeft)
        leftSplitter.addWidget(self._topLeft)
        leftSplitter.setStretchFactor(1, 1)
        vbox.addWidget(leftSplitter)

        vbox = QVBoxLayout(self._right)
        vbox.setContentsMargins(0, 0, 0, 0)

        rightSplitter = QSplitter(QtCore.Qt.Vertical)
        rightSplitter.addWidget(self._botRight)
        rightSplitter.addWidget(self._topRight)
        rightSplitter.setStretchFactor(1, 1)
        vbox.addWidget(rightSplitter)

        minimumSize = QSize(200, 200)
        self._botLeft.setMinimumSize(minimumSize)
        self._botRight.setMinimumSize(minimumSize)
        self._topLeft.setMinimumSize(minimumSize)
        self._topRight.setMinimumSize(minimumSize)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._setEqualSize:
            self.setEqualSize()

        self._setEqualSize = False

    def setEqualSize(self):
        if not self.isVisible():
            self._setEqualSize = True

        halfSizeLeft = QSize(self.width()/2, self.height())
        self._left.resize(halfSizeLeft)

        halfSize = QSize(self._left.width(), self._left.height()/2)
        self._botLeft.resize(halfSize)
        self._botRight.resize(halfSize)
        self._topLeft.resize(halfSize)
        self._topRight.resize(halfSize)