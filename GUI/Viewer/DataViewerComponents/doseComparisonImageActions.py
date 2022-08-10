import os
from typing import Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QComboBox, QWidgetAction

from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer
from GUI.Viewer.DataViewerComponents.doseComparisonImageProvider import DoseComparisonImageProvider
from GUI.Viewer.DataViewerComponents.imageFusionPropEditor import ImageFusionPropEditor
from GUI.Viewer.DataViewerComponents.dataViewerToolbar import DataViewerToolbar
from GUI.Viewer.DataViewerComponents.image3DViewer import Image3DViewer


class DoseComparisonImageActions:
    def __init__(self, imageViewer:Image3DViewer, dataViewer):
        self._dataViewer = dataViewer
        self._imageViewer = imageViewer
        self._image = imageViewer.secondaryImageLayer.image
        self._secondaryImageLayer = imageViewer.secondaryImageLayer

        self._metricsStr = ["Difference", "Absolute difference", "Gamma"]
        self._metrics = [DoseComparisonImageProvider.Metric.DIFFERENCE, DoseComparisonImageProvider.Metric.ABSOLUTE_DIFFERENCE, DoseComparisonImageProvider.Metric.GAMMA]

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        self._separator = None

        self._colorbarAction = QAction(QIcon(iconPath + "colormap_jet.png"), "Colorbar")
        self._colorbarAction.setStatusTip("Colorbar")
        self._colorbarAction.triggered.connect(self._setColorbarOn)
        self._colorbarAction.setCheckable(True)

        self._rangeAction = QAction(QIcon(iconPath + "color-adjustment.png"), "Range")
        self._rangeAction.setStatusTip("Range")
        self._rangeAction.triggered.connect(self._showImageProperties)

        self._metricsCombo = QComboBox()
        self._metricsCombo.currentIndexChanged.connect(self._handleMetric)
        self._metricsCombo.addItem(self._metricsStr[0])
        self._metricsCombo.addItem(self._metricsStr[1])
        self._metricsCombo.addItem(self._metricsStr[2])
        currentIndex = self._metrics.index(self._dataViewer.comparisonMetric)
        self._metricsCombo.setCurrentIndex(currentIndex)
        self._metricsAction = QWidgetAction(None)
        self._metricsAction.setDefaultWidget(self._metricsCombo)

        self._resetVisibility()
        self._secondaryImageLayer.imageChangedSignal.connect(self._updateImage)
        #TODO: connect to colorbarSignal

    def addToToolbar(self, toolbar:DataViewerToolbar):
        self._separator = toolbar.addSeparator()
        toolbar.addAction(self._colorbarAction)
        toolbar.addAction(self._rangeAction)
        toolbar.addAction(self._metricsAction)

        self._resetVisibility()

    def hide(self):
        if not self._separator is None:
            self._separator.setVisible(False)
        self._colorbarAction.setVisible(False)
        self._rangeAction.setVisible(False)
        self._metricsAction.setVisible(False)

    def show(self):
        self._resetVisibility()

    def _resetVisibility(self):
        if self._image is None:
            self.hide()
        else:
            if not self._separator is None:
                self._separator.setVisible(True)
            self._colorbarAction.setVisible(True)
            self._colorbarAction.setChecked(self._secondaryImageLayer.colorbarOn)
            self._rangeAction.setVisible(True)
            self._metricsAction.setVisible(True)

    def _setColorbarOn(self, visible: bool):
        self._secondaryImageLayer.colorbarOn = visible

    def _showImageProperties(self):
        self._imageFusionProp = ImageFusionPropEditor(self._image.data)
        self._imageFusionProp.show()

    def _updateImage(self, image: Optional[Image3DForViewer]):
        self._image = image
        self._resetVisibility()

    def _handleMetric(self):
        self._dataViewer.comparisonMetric = self._metrics[self._metricsCombo.currentIndex()]
