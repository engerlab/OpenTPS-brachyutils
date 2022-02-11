import os
from typing import Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction

from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer
from GUI.Viewer.DataViewerComponents.imageFusionPropEditor import ImageFusionPropEditor
from GUI.Viewer.DataViewerComponents.ImageViewerComponents.secondaryImageLayer import SecondaryImageLayer
from GUI.Viewer.DataViewerComponents.dataViewerToolbar import DataViewerToolbar


class SecondaryImageActions:
    def __init__(self, secondaryImageLayer: SecondaryImageLayer):
        self._image = secondaryImageLayer.image
        self._secondaryImageLayer = secondaryImageLayer

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        self._separator = None

        self._colorbarAction = QAction(QIcon(iconPath + "color.png"), "Colorbar")
        self._colorbarAction.setStatusTip("Colorbar")
        self._colorbarAction.triggered.connect(self._setColorbarOn)
        self._colorbarAction.setCheckable(True)

        self._rangeAction = QAction(QIcon(iconPath + "color-adjustment.png"), "Range")
        self._rangeAction.setStatusTip("Range")
        self._rangeAction.triggered.connect(self._showImageProperties)

        self._resetVisibility()
        self._secondaryImageLayer.imageChangedSignal.connect(self._updateImage)
        #TODO: connect to colorbarSignal

    def addToToolbar(self, toolbar:DataViewerToolbar):
        self._separator = toolbar.addSeparator()
        toolbar.addAction(self._colorbarAction)
        toolbar.addAction(self._rangeAction)

        self._resetVisibility()

    def hide(self):
        if not self._separator is None:
            self._separator.setVisible(False)
        self._colorbarAction.setVisible(False)
        self._rangeAction.setVisible(False)

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

    def _setColorbarOn(self, visible: bool):
        self._secondaryImageLayer.colorbarOn = visible

    def _showImageProperties(self):
        self._imageFusionProp = ImageFusionPropEditor(self._image.data)
        self._imageFusionProp.show()

    def _updateImage(self, image: Optional[Image3DForViewer]):
        self._image = image
        self._resetVisibility()

