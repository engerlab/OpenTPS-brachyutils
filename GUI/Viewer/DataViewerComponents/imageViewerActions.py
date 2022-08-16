import functools

import matplotlib
from PyQt5.QtWidgets import QComboBox, QWidgetAction, QMenu, QAction

from GUI.Viewer.DataViewerComponents.dataViewerToolbar import DataViewerToolbar
from GUI.Viewer.DataViewerComponents.doseComparisonImageProvider import DoseComparisonImageProvider
from GUI.Viewer.DataViewerComponents.image3DViewer import Image3DViewer
from GUI.Viewer.DataViewerComponents.imageFusionPropEditor import ImageFusionPropEditor


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

        self._secondaryImageMenu = SecondaryImageMenu(self._imageViewer)
        self._primaryImageMenu = PrimaryImageMenu()
        self._doseComparisonMenu = DoseComparisonMenu(self._imageViewer)

        self.hide()

        self._viewTypeCombo.setCurrentIndex(self._viewTypeToIndex(self._imageViewer.viewType))
        self._viewTypeCombo.currentIndexChanged.connect(self._handleViewTypeSelection)
        self._imageViewer.viewTypeChangedSignal.connect(self._handleExternalViewTypeChange)

    @property
    def doseComparisonDataViewer(self):
        return self._doseComparisonMenu.dataViewer

    @doseComparisonDataViewer.setter
    def doseComparisonDataViewer(self, dataViewer):
        self._doseComparisonMenu.dataViewer = dataViewer


    def _viewTypeToIndex(self, viewType):
        return list(self._viewTypeToStr.keys()).index(viewType)

    def setImageViewer(self, imageViewer):
        self._imageViewer = imageViewer

    def addToToolbar(self, toolbar:DataViewerToolbar):
        self._separator = toolbar.addSeparator()
        toolbar.addAction(self._viewTypeAction)
        toolbar.toolsMenu.addMenu(self._primaryImageMenu)
        toolbar.toolsMenu.addMenu(self._secondaryImageMenu)
        toolbar.toolsMenu.addMenu(self._doseComparisonMenu)

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


class PrimaryImageMenu(QMenu):
    def __init__(self):
        super().__init__("Primary image")

        self._wwlAction = QAction("Window level", self)
        self.addAction(self._wwlAction)

class SecondaryImageMenu(QMenu):
    def __init__(self, imageViewer:Image3DViewer):
        super().__init__("Secondary image")

        self._imageViewer = imageViewer
        self._secondaryImageLayer = self._imageViewer.secondaryImageLayer

        self._resetAction = QAction("Reset", self)
        self._resetAction.triggered.connect(self._resetImage)
        self.addAction(self._resetAction)

        self._colorMapMenu = QMenu("Colormap", self)
        self.addMenu(self._colorMapMenu)

        self._colormapActions = []
        cms = matplotlib.pyplot.colormaps()

        for cm in cms:
            cmAction = QAction(cm, self._colorMapMenu)
            cmAction.triggered.connect(functools.partial(self.setFusion, cm))
            self._colorMapMenu.addAction(cmAction)
            self._colormapActions.append(cmAction)

        self._colorbarAction = QAction("Show/hide colorbar", self)
        self._colorbarAction.triggered.connect(self._setColorbarOnOff)
        self.addAction(self._colorbarAction)

        self._wwlAction = QAction("Window level", self)
        self._wwlAction.triggered.connect(self._showImageProperties)
        self.addAction(self._wwlAction)

    def _resetImage(self):
        self._imageViewer.secondaryImage = None

    def _setColorbarOnOff(self):
        self._secondaryImageLayer.colorbarOn = not self._secondaryImageLayer.colorbarOn

    def _showImageProperties(self):
        self._imageFusionProp = ImageFusionPropEditor(self._secondaryImageLayer.image.data)
        self._imageFusionProp.show()

    def setFusion(self, name:str):
        self._imageViewer.secondaryImageLayer.image.lookupTableName = name

class DoseComparisonMenu(QMenu):
    def __init__(self, imageViewer:Image3DViewer):
        super().__init__("Dose comparison")

        self.dataViewer = None

        self._imageViewer = imageViewer
        self._secondaryImageLayer = self._imageViewer.secondaryImageLayer

        self._metricsMenu = QMenu("Metrics", self)
        self.addMenu(self._metricsMenu)

        self._diffAction = QAction("Difference", self._metricsMenu)
        self._diffAction.triggered.connect(self._setDiffMetric)
        self._metricsMenu.addAction(self._diffAction)
        self._absDiffAction = QAction("Absolute difference", self._metricsMenu)
        self._absDiffAction.triggered.connect(self._setAbsDiffMetric)
        self._metricsMenu.addAction(self._absDiffAction)
        self._gammaAction = QAction("Gamma", self._metricsMenu)
        self._gammaAction.triggered.connect(self._setGammaMetric)
        self._metricsMenu.addAction(self._gammaAction)

        self._colorMapMenu = QMenu("Colormap", self)
        self.addMenu(self._colorMapMenu)

        self._colormapActions = []
        cms = matplotlib.pyplot.colormaps()

        for cm in cms:
            cmAction = QAction(cm, self._colorMapMenu)
            cmAction.triggered.connect(functools.partial(self.setFusion, cm))
            self._colorMapMenu.addAction(cmAction)
            self._colormapActions.append(cmAction)

        self._colorbarAction = QAction("Show/hide colorbar", self)
        self._colorbarAction.triggered.connect(self._setColorbarOnOff)
        self.addAction(self._colorbarAction)

        self._wwlAction = QAction("Window level", self)
        self._wwlAction.triggered.connect(self._showImageProperties)
        self.addAction(self._wwlAction)

    def _setColorbarOnOff(self):
        self._secondaryImageLayer.colorbarOn = not self._secondaryImageLayer.colorbarOn

    def _showImageProperties(self):
        self._imageFusionProp = ImageFusionPropEditor(self._secondaryImageLayer.image.data)
        self._imageFusionProp.show()

    def _setDiffMetric(self):
        self.dataViewer.comparisonMetric = DoseComparisonImageProvider.Metric.DIFFERENCE
    def _setAbsDiffMetric(self):
        self.dataViewer.comparisonMetric = DoseComparisonImageProvider.Metric.ABSOLUTE_DIFFERENCE
    def _setGammaMetric(self):
        self.dataViewer.comparisonMetric = DoseComparisonImageProvider.Metric.GAMMA

    def setFusion(self, name:str):
        self._imageViewer.secondaryImageLayer.lookupTableName = name
