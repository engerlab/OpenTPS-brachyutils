from PyQt5 import QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QHBoxLayout, QFrame, QSplitter, QVBoxLayout

from GUI.Viewer.doseComparisonDataViewer import DoseComparisonDataViewer
from GUI.Viewer.grid import Grid
from GUI.Viewer.dataViewer import DataViewer


class GridFourElements(Grid):
    def __init__(self, viewController):
        Grid.__init__(self, viewController)

        self._minimumSize = QSize(200, 200)
        self._setEqualSize = False #Use to set equal size before qwidget is effectively shown

        # Containers for the 4 grid elements
        self._botLeftGridElementContainer = QFrame(self)
        self._botRightGridElementContainer = QFrame(self)
        self._topLeftGridElementContainer = QFrame(self)
        self._topRightGridElementContainer = QFrame(self)

        # Layouts for the 4 grid elements
        self._botLeftLayout = QVBoxLayout(self._botLeftGridElementContainer)
        self._botRightLayout = QVBoxLayout(self._botRightGridElementContainer)
        self._topLeftLayout = QVBoxLayout(self._topLeftGridElementContainer)
        self._topRightLayout = QVBoxLayout(self._topRightGridElementContainer)

        # Set shape, size and margins
        self._botLeftGridElementContainer.setFrameShape(QFrame.StyledPanel)
        self._botRightGridElementContainer.setFrameShape(QFrame.StyledPanel)
        self._topLeftGridElementContainer.setFrameShape(QFrame.StyledPanel)
        self._topRightGridElementContainer.setFrameShape(QFrame.StyledPanel)

        self._botLeftLayout.setContentsMargins(0, 0, 0, 0)
        self._botRightLayout.setContentsMargins(0, 0, 0, 0)
        self._topLeftLayout.setContentsMargins(0, 0, 0, 0)
        self._topRightLayout.setContentsMargins(0, 0, 0, 0)

        self._botLeftGridElementContainer.setMinimumSize(self._minimumSize)
        self._botRightGridElementContainer.setMinimumSize(self._minimumSize)
        self._topLeftGridElementContainer.setMinimumSize(self._minimumSize)
        self._topRightGridElementContainer.setMinimumSize(self._minimumSize)

        # Horizontal splitting
        self._mainLayout = QHBoxLayout(self)

        self._leftPart = QFrame(self)
        self._leftPart.setFrameShape(QFrame.StyledPanel)

        self._rightPart = QFrame(self)
        self._rightPart.setFrameShape(QFrame.StyledPanel)

        self._horizontalSplitter = QSplitter(QtCore.Qt.Horizontal)
        self._horizontalSplitter.addWidget(self._leftPart)
        self._horizontalSplitter.addWidget(self._rightPart)
        self._horizontalSplitter.setStretchFactor(1, 1)

        self._mainLayout.addWidget(self._horizontalSplitter)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        # Vertical splitting
        leftPartLayout = QVBoxLayout(self._leftPart)
        leftPartLayout.setContentsMargins(0, 0, 0, 0)

        leftPartSplitter = QSplitter(QtCore.Qt.Vertical)
        leftPartSplitter.addWidget(self._topLeftGridElementContainer)
        leftPartSplitter.addWidget(self._botLeftGridElementContainer)
        leftPartSplitter.setStretchFactor(1, 1)
        leftPartLayout.addWidget(leftPartSplitter)

        rightPartLayout = QVBoxLayout(self._rightPart)
        rightPartLayout.setContentsMargins(0, 0, 0, 0)

        rightPartSplitter = QSplitter(QtCore.Qt.Vertical)
        rightPartSplitter.addWidget(self._topRightGridElementContainer)
        rightPartSplitter.addWidget(self._botRightGridElementContainer)
        rightPartSplitter.setStretchFactor(1, 1)
        rightPartLayout.addWidget(rightPartSplitter)

        self._initializeViewers()

    def _initializeViewers(self):
        # Fill grid elements with data viewers
        gridElement = DoseComparisonDataViewer(self._viewController)
        gridElement.cachedStaticImage3DViewer.viewType = gridElement.cachedStaticImage3DViewer.ViewerTypes.AXIAL
        gridElement.cachedStaticImage2DViewer.viewType = gridElement.cachedStaticImage2DViewer.ViewerTypes.AXIAL
        gridElement.cachedDynamicImage3DViewer.viewType = gridElement.cachedDynamicImage3DViewer.ViewerTypes.AXIAL
        gridElement.cachedDynamicImage2DViewer.viewType = gridElement.cachedDynamicImage2DViewer.ViewerTypes.AXIAL
        self.appendGridElement(gridElement)
        self._topLeftLayout.addWidget(gridElement)
        gridElement = DoseComparisonDataViewer(self._viewController)
        gridElement.cachedStaticImage3DViewer.viewType = gridElement.cachedStaticImage3DViewer.ViewerTypes.CORONAL
        gridElement.cachedStaticImage2DViewer.viewType = gridElement.cachedStaticImage2DViewer.ViewerTypes.CORONAL
        gridElement.cachedDynamicImage3DViewer.viewType = gridElement.cachedDynamicImage3DViewer.ViewerTypes.CORONAL
        gridElement.cachedDynamicImage2DViewer.viewType = gridElement.cachedDynamicImage2DViewer.ViewerTypes.CORONAL
        self.appendGridElement(gridElement)
        self._topRightLayout.addWidget(gridElement)
        gridElement = DoseComparisonDataViewer(self._viewController)
        gridElement.cachedStaticImage3DViewer.viewType = gridElement.cachedStaticImage3DViewer.ViewerTypes.SAGITTAL
        gridElement.cachedStaticImage2DViewer.viewType = gridElement.cachedStaticImage2DViewer.ViewerTypes.SAGITTAL
        gridElement.cachedDynamicImage3DViewer.viewType = gridElement.cachedDynamicImage3DViewer.ViewerTypes.SAGITTAL
        gridElement.cachedDynamicImage2DViewer.viewType = gridElement.cachedDynamicImage2DViewer.ViewerTypes.SAGITTAL
        self.appendGridElement(gridElement)
        self._botLeftLayout.addWidget(gridElement)
        gridElement = DoseComparisonDataViewer(self._viewController)
        gridElement.cachedStaticImage3DViewer.viewType = gridElement.cachedStaticImage3DViewer.ViewerTypes.SAGITTAL
        self.appendGridElement(gridElement)
        self._botRightLayout.addWidget(gridElement)


    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._setEqualSize:
            self.setEqualSize()
        self._setEqualSize = False

    def setEqualSize(self):
        if not self.isVisible():
            self._setEqualSize = True

        # We first resize left part and then we resize everything which has the side effect to resize right part
        leftPartHalfSize = QSize(int(self.width()/2), self.height())
        self._leftPart.resize(leftPartHalfSize)

        halfSize = QSize(self._leftPart.width(), int(self._leftPart.height() / 2))
        self._botLeftGridElementContainer.resize(halfSize)
        self._botRightGridElementContainer.resize(halfSize)
        self._topLeftGridElementContainer.resize(halfSize)
        self._topRightGridElementContainer.resize(halfSize)
