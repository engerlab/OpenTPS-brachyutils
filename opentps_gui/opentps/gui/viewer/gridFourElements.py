from PyQt5 import QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QHBoxLayout, QFrame, QSplitter, QVBoxLayout

from opentps.gui.viewer.doseComparisonDataViewer import DoseComparisonDataViewer
from opentps.gui.viewer.grid import Grid


class GridFourElements(Grid):
    def __init__(self, viewController, parent):
        super().__init__(viewController, parent)

        self._minimumSize = QSize(200, 200)
        self._setEqualSize = False #Use to set equal size before qwidget is effectively shown

        # Horizontal splitting
        self._mainLayout = QHBoxLayout(self)

        self._horizontalSplitter = QSplitter(QtCore.Qt.Horizontal, self)
        self._leftPart = QFrame(self._horizontalSplitter)
        self._leftPart.setFrameShape(QFrame.StyledPanel)
        self._rightPart = QFrame(self._horizontalSplitter)
        self._rightPart.setFrameShape(QFrame.StyledPanel)
        self._horizontalSplitter.addWidget(self._leftPart)
        self._horizontalSplitter.addWidget(self._rightPart)
        self._horizontalSplitter.setStretchFactor(1, 1)

        self._mainLayout.addWidget(self._horizontalSplitter)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        # Vertical splitting
        leftPartLayout = QVBoxLayout(self._leftPart)
        leftPartLayout.setContentsMargins(0, 0, 0, 0)
        rightPartLayout = QVBoxLayout(self._rightPart)
        rightPartLayout.setContentsMargins(0, 0, 0, 0)

        self._leftPartSplitter = VerticalSplitter(self)
        self._botLeftGridElementContainer = self._leftPartSplitter.botGridElementContainer
        self._topLeftGridElementContainer = self._leftPartSplitter.topGridElementContainer
        leftPartLayout.addWidget(self._leftPartSplitter)

        self._rightPartSplitter = VerticalSplitter(self)
        self._botRightGridElementContainer = self._rightPartSplitter.botGridElementContainer
        self._topRightGridElementContainer = self._rightPartSplitter.topGridElementContainer
        rightPartLayout.addWidget(self._rightPartSplitter)

        self._botLeftGridElementContainer.setMinimumSize(self._minimumSize)
        self._botRightGridElementContainer.setMinimumSize(self._minimumSize)
        self._topLeftGridElementContainer.setMinimumSize(self._minimumSize)
        self._topRightGridElementContainer.setMinimumSize(self._minimumSize)

        self._botLeftLayout = QVBoxLayout(self._botLeftGridElementContainer)
        self._botRightLayout = QVBoxLayout(self._botRightGridElementContainer)
        self._topLeftLayout = QVBoxLayout(self._topLeftGridElementContainer)
        self._topRightLayout = QVBoxLayout(self._topRightGridElementContainer)

        self._botLeftLayout.setContentsMargins(0, 0, 0, 0)
        self._botRightLayout.setContentsMargins(0, 0, 0, 0)
        self._topLeftLayout.setContentsMargins(0, 0, 0, 0)
        self._topRightLayout.setContentsMargins(0, 0, 0, 0)

        self._initializeViewers()

    def closeEvent(self, QCloseEvent):

        super().closeEvent(QCloseEvent)

    def _initializeViewers(self):
        # Fill grid elements with data viewers
        gridElement = DoseComparisonDataViewer(self._viewController)
        gridElement.cachedStaticImage3DViewer.viewType = gridElement.cachedStaticImage3DViewer.ViewerTypes.AXIAL
        # gridElement.cachedStaticImage2DViewer.viewType = gridElement.cachedStaticImage2DViewer.ViewerTypes.AXIAL
        gridElement.cachedDynamicImage3DViewer.viewType = gridElement.cachedDynamicImage3DViewer.ViewerTypes.AXIAL
        # gridElement.cachedDynamicImage2DViewer.viewType = gridElement.cachedDynamicImage2DViewer.ViewerTypes.AXIAL
        self.appendGridElement(gridElement)
        self._topLeftLayout.addWidget(gridElement)
        gridElement = DoseComparisonDataViewer(self._viewController)
        gridElement.cachedStaticImage3DViewer.viewType = gridElement.cachedStaticImage3DViewer.ViewerTypes.CORONAL
        # gridElement.cachedStaticImage2DViewer.viewType = gridElement.cachedStaticImage2DViewer.ViewerTypes.CORONAL
        gridElement.cachedDynamicImage3DViewer.viewType = gridElement.cachedDynamicImage3DViewer.ViewerTypes.CORONAL
        # gridElement.cachedDynamicImage2DViewer.viewType = gridElement.cachedDynamicImage2DViewer.ViewerTypes.CORONAL
        self.appendGridElement(gridElement)
        self._topRightLayout.addWidget(gridElement)
        gridElement = DoseComparisonDataViewer(self._viewController)
        gridElement.cachedStaticImage3DViewer.viewType = gridElement.cachedStaticImage3DViewer.ViewerTypes.SAGITTAL
        # gridElement.cachedStaticImage2DViewer.viewType = gridElement.cachedStaticImage2DViewer.ViewerTypes.SAGITTAL
        gridElement.cachedDynamicImage3DViewer.viewType = gridElement.cachedDynamicImage3DViewer.ViewerTypes.SAGITTAL
        # gridElement.cachedDynamicImage2DViewer.viewType = gridElement.cachedDynamicImage2DViewer.ViewerTypes.SAGITTAL
        self.appendGridElement(gridElement)
        self._botLeftLayout.addWidget(gridElement)
        gridElement = DoseComparisonDataViewer(self._viewController)
        gridElement.cachedStaticImage3DViewer.viewType = gridElement.cachedStaticImage3DViewer.ViewerTypes.SAGITTAL
        self.appendGridElement(gridElement)
        self._botRightLayout.addWidget(gridElement)


    def resizeEvent(self, event):
        if self._setEqualSize:
            self.setEqualSize()
        self._setEqualSize = False

        self._oldWidth = event.oldSize().width()
        self._newWidth = event.size().width()
        self._leftWidth = self._horizontalSplitter.sizes()[0]

        if self._oldWidth<=0 or self._oldWidth==self.width():
            super().resizeEvent(event)
            return

        oldWidthRatio = self._leftWidth / self._oldWidth

        leftPartWidth = int(oldWidthRatio * self._newWidth)
        rightPartWidth = int(self._newWidth - oldWidthRatio * self._newWidth)

        self._horizontalSplitter.setSizes([leftPartWidth, rightPartWidth])

        super().resizeEvent(event)


    def setEqualSize(self):
        if not self.isVisible():
            self._setEqualSize = True

        leftPartWidth = int(self.width()/2)
        self._horizontalSplitter.setSizes([leftPartWidth, leftPartWidth])

        self._leftPartSplitter.setEqualSize()
        self._rightPartSplitter.setEqualSize()


class VerticalSplitter(QSplitter):
    def __init__(self, parent):
        super().__init__(QtCore.Qt.Vertical, parent)

        self._setEqualSize = False  # Use to set equal size before qwidget is effectively shown

        self.botGridElementContainer = QFrame(self)
        self.topGridElementContainer = QFrame(self)
        self.addWidget(self.topGridElementContainer)
        self.addWidget(self.botGridElementContainer)
        self.setStretchFactor(1, 1)

        self.botGridElementContainer.setFrameShape(QFrame.StyledPanel)
        self.topGridElementContainer.setFrameShape(QFrame.StyledPanel)

    def resizeEvent(self, event):
        if self._setEqualSize:
            self.setEqualSize()
        self._setEqualSize = False

        self._oldHeight = event.oldSize().height()
        self._newHeight = event.size().height()
        self._topHeight = self.sizes()[0]

        if self._oldHeight<=0 or self._oldHeight==self._newHeight:
            super().resizeEvent(event)
            return

        oldHeightRatio = self._topHeight/self._oldHeight

        topHeight = int(oldHeightRatio * self._newHeight)
        botHeight = int(self._newHeight - oldHeightRatio*self._newHeight)

        self.setSizes([topHeight, botHeight])

    def setEqualSize(self):
        if not self.isVisible():
            self._setEqualSize = True

        topHeight = int(self.height()/2)
        self.setSizes([topHeight, topHeight])
