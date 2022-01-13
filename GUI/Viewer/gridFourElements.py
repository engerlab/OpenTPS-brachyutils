from PyQt5 import QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QHBoxLayout, QFrame, QSplitter, QVBoxLayout

from GUI.Viewer.grid import Grid
from GUI.Viewer.gridElement import GridElement
from GUI.Viewer.Viewers.sliceViewer import SliceViewerVTK


class GridFourElements(Grid):
    def __init__(self, viewController):
        Grid.__init__(self, viewController)

        self._setEqualSize = False #Use to set equal size before qwidget is effectively shown

        self._botLeft = QFrame(self)
        self._botRight = QFrame(self)
        self._topLeft = QFrame(self)
        self._topRight = QFrame(self)

        self._botLeft.setFrameShape(QFrame.StyledPanel)
        self._botRight.setFrameShape(QFrame.StyledPanel)
        self._topLeft.setFrameShape(QFrame.StyledPanel)
        self._topRight.setFrameShape(QFrame.StyledPanel)

        self._leftSize = None
        self._rightSize = None
        self._size = None

        self._botLeftLayout = QVBoxLayout(self._botLeft)
        self._botRightLayout = QVBoxLayout(self._botRight)
        self._topLeftLayout = QVBoxLayout(self._topLeft)
        self._topRightLayout = QVBoxLayout(self._topRight)

        self._botLeftLayout.setContentsMargins(0, 0, 0, 0)
        self._botRightLayout.setContentsMargins(0, 0, 0, 0)
        self._topLeftLayout.setContentsMargins(0, 0, 0, 0)
        self._topRightLayout.setContentsMargins(0, 0, 0, 0)

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
        leftSplitter.addWidget(self._topLeft)
        leftSplitter.addWidget(self._botLeft)
        leftSplitter.setStretchFactor(1, 1)
        vbox.addWidget(leftSplitter)

        vbox = QVBoxLayout(self._right)
        vbox.setContentsMargins(0, 0, 0, 0)

        rightSplitter = QSplitter(QtCore.Qt.Vertical)
        rightSplitter.addWidget(self._topRight)
        rightSplitter.addWidget(self._botRight)
        rightSplitter.setStretchFactor(1, 1)
        vbox.addWidget(rightSplitter)

        minimumSize = QSize(200, 200)
        self._botLeft.setMinimumSize(minimumSize)
        self._botRight.setMinimumSize(minimumSize)
        self._topLeft.setMinimumSize(minimumSize)
        self._topRight.setMinimumSize(minimumSize)

        gridElement = GridElement(self._viewController)
        if isinstance(gridElement.currentViewer, SliceViewerVTK):
            gridElement.currentViewer.setView('axial')
        self.appendGridElement(gridElement)
        self._botLeftLayout.addWidget(gridElement)
        gridElement = GridElement(self._viewController)
        if isinstance(gridElement.currentViewer, SliceViewerVTK):
            gridElement.currentViewer.setView('axial')
        self.appendGridElement(gridElement)
        self._botRightLayout.addWidget(gridElement)
        gridElement = GridElement(self._viewController)
        if isinstance(gridElement.currentViewer, SliceViewerVTK):
            gridElement.currentViewer.setView('coronal')
        self.appendGridElement(gridElement)
        self._topLeftLayout.addWidget(gridElement)
        gridElement = GridElement(self._viewController)
        if isinstance(gridElement.currentViewer, SliceViewerVTK):
            gridElement.currentViewer.setView('sagittal')
        self.appendGridElement(gridElement)
        self._topRightLayout.addWidget(gridElement)


    def resizeEvent(self, event):
        super().resizeEvent(event)


        if not self._leftSize is None:
            return
            #This does not work
            width_factor = self.width() / self._size[0]
            height_factor = self.height() / self._size[1]

            print((width_factor, height_factor))

            self._left.resize(QSize(self._leftSize[0]*width_factor, self._leftSize[1]*height_factor))
            self._right.resize(QSize(self._rightSize[0] * width_factor, self._rightSize[1] * height_factor))


        if self._setEqualSize:
            self.setEqualSize()
        self._setEqualSize = False

        self._leftSize = (self._left.width(), self._left.height())
        self._rightSize = (self._right.width(), self._right.height())
        self._size = (self.width(), self.height())

    def setEqualSize(self):
        if not self.isVisible():
            self._setEqualSize = True

        halfSizeLeft = QSize(int(self.width()/2), self.height())
        self._left.resize(halfSizeLeft)

        halfSize = QSize(self._left.width(), int(self._left.height()/2))
        self._botLeft.resize(halfSize)
        self._botRight.resize(halfSize)
        self._topLeft.resize(halfSize)
        self._topRight.resize(halfSize)
