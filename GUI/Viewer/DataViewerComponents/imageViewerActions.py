from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QAction, QComboBox, QLabel, QWidgetAction

from GUI.Viewer.DataViewerComponents.dataViewerToolbar import DataViewerToolbar
from GUI.Viewer.DataViewerComponents.imageViewer import ImageViewer


class ImageViewerActions:
    def __init__(self, imageViewer: ImageViewer):
        self._imageViewer = imageViewer

        self._viewTypeToStr = {self._imageViewer.viewerTypes.AXIAL: 'Axial',
                               self._imageViewer.viewerTypes.CORONAL: 'Coronal',
                               self._imageViewer.viewerTypes.SAGITTAL: 'Sagittal'}
        self._strToViewType = {v: k for k, v in self._viewTypeToStr.items()}

        self._separator = None

        self._viewTypeCombo = QComboBox()
        self._viewTypeCombo.setFixedSize(80, 16)
        self._viewTypeCombo.addItems(list(self._viewTypeToStr.values()))

        self._viewTypeAction = QWidgetAction(None)
        self._viewTypeAction.setDefaultWidget(self._viewTypeCombo)

        self.hide()

        self._viewTypeCombo.setCurrentIndex(self._viewTypeToIndex(self._imageViewer.viewType))

        self._viewTypeCombo.currentIndexChanged.connect(self._handleViewTypeSelection)

        self._imageViewer.viewTypeChangedSignal.connect(self._handleExternalViewTypeChange)

    def _viewTypeToIndex(self, viewType):
        return list(self._viewTypeToStr.keys()).index(viewType)

    def setImageViewer(self, imageViewer):
        self._imageViewer = imageViewer

    def addToToolbar(self, toolbar:DataViewerToolbar):
        self._separator = toolbar.addSeparator()
        toolbar.addAction(self._viewTypeAction)

    def hide(self):
        if not self._separator is None:
            self._separator.setVisible(False)
        self._viewTypeAction.setVisible(False)

    def show(self):
        self._separator.setVisible(True)
        self._viewTypeAction.setVisible(True)

    def _handleViewTypeSelection(self, selectionIndex):
        selectionText = self._viewTypeCombo.itemText(selectionIndex)
        self._imageViewer.viewType = self._strToViewType[selectionText]

    def _handleExternalViewTypeChange(self, viewType):
        self._viewTypeCombo.setCurrentIndex(self._viewTypeToIndex(viewType))
