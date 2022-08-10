
from PyQt5.QtWidgets import QComboBox, QWidgetAction, QPushButton

from GUI.Viewer.DataViewerComponents.dataViewerToolbar import DataViewerToolbar
from GUI.Viewer.DataViewerComponents.image3DViewer import Image3DViewer


class ImageViewerActions:
    def __init__(self, imageViewer:Image3DViewer):
        self._imageViewer = imageViewer

        self._viewTypeToStr = {self._imageViewer.ViewerTypes.AXIAL: 'Axial',
                               self._imageViewer.ViewerTypes.CORONAL: 'Coronal',
                               self._imageViewer.ViewerTypes.SAGITTAL: 'Sagittal'}
        self._strToViewType = {v: k for k, v in self._viewTypeToStr.items()}

        self._separator = None

        self._viewTypeCombo = QComboBox()
        self._viewTypeCombo.setFixedSize(80, 16)
        self._viewTypeCombo.addItems(list(self._viewTypeToStr.values()))

        self._viewTypeAction = QWidgetAction(None)
        self._viewTypeAction.setDefaultWidget(self._viewTypeCombo)

        self._resetSecondaryImgButton = QPushButton('Reset secondary img')
        self._resetSecondaryImgButton.setFixedHeight(16)
        self._resetSecondaryImgButton.clicked.connect(self._resetSecondaryImg)
        self._resetSecondaryImgAction = QWidgetAction(None)
        self._resetSecondaryImgAction.setDefaultWidget(self._resetSecondaryImgButton)

        self._handleSecondaryImage()

        self.hide()

        self._viewTypeCombo.setCurrentIndex(self._viewTypeToIndex(self._imageViewer.viewType))
        self._viewTypeCombo.currentIndexChanged.connect(self._handleViewTypeSelection)
        self._imageViewer.viewTypeChangedSignal.connect(self._handleExternalViewTypeChange)
        self._imageViewer.secondaryImageSignal.connect(self._handleSecondaryImage)


    def _viewTypeToIndex(self, viewType):
        return list(self._viewTypeToStr.keys()).index(viewType)

    def setImageViewer(self, imageViewer):
        self._imageViewer = imageViewer

    def addToToolbar(self, toolbar:DataViewerToolbar):
        self._separator = toolbar.addSeparator()
        toolbar.addAction(self._viewTypeAction)
        toolbar.addAction(self._resetSecondaryImgAction)

    def hide(self):
        if not self._separator is None:
            self._separator.setVisible(False)
        self._viewTypeAction.setVisible(False)
        self._resetSecondaryImgAction.setVisible(False)

    def show(self):
        self._separator.setVisible(True)
        self._viewTypeAction.setVisible(True)
        self._handleSecondaryImage()

    def _handleViewTypeSelection(self, selectionIndex):
        selectionText = self._viewTypeCombo.itemText(selectionIndex)
        self._imageViewer.viewType = self._strToViewType[selectionText]

    def _handleExternalViewTypeChange(self, viewType):
        self._viewTypeCombo.setCurrentIndex(self._viewTypeToIndex(viewType))

    def _resetSecondaryImg(self):
        self._imageViewer.secondaryImage = None

    def _handleSecondaryImage(self, *args):
        if self._imageViewer.secondaryImage is None:
            self._resetSecondaryImgAction.setVisible(False)
        else:
            self._resetSecondaryImgAction.setVisible(True)