import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction

from GUI.Viewer.Viewers.imageFusionProperties import ImageFusionProperties


class SecondaryImageActions:
    def __init__(self, secondaryImageLayer):
        self._actions = []

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep

        self._colorbarAction = QAction(QIcon(iconPath + "color.png"), "Colorbar")
        self._image = None
        self._rangeAction = QAction(QIcon(iconPath + "color-adjustment.png"), "Range")
        self._secondaryImageLayer = secondaryImageLayer

        if not secondaryImageLayer.image is None:
            self._image = secondaryImageLayer.image.data

        self._colorbarAction.setStatusTip("Colorbar")
        self._colorbarAction.triggered.connect(self._setColorbarOn)
        self._colorbarAction.setCheckable(True)
        self._rangeAction.setStatusTip("Range")
        self._rangeAction.triggered.connect(self._showImageProperties)

        self._actions.append(self._colorbarAction)
        self._actions.append(self._rangeAction)

        self._updateImage(self._image) #TO update visibility
        self._secondaryImageLayer.imageChangedSignal.connect(self._updateImage)
        #TODO: connect to colorbarSignal

    def _setColorbarOn(self, visible):
        self._secondaryImageLayer.colorbarOn = visible

    def _showImageProperties(self):
        ImageFusionProperties(self._image).show()

    def _updateImage(self, image):
        if image is None:
            self._image = None
            self._colorbarAction.setVisible(False)
            self._rangeAction.setVisible(False)
        else:
            self._image = image.data
            self._colorbarAction.setVisible(True)
            self._colorbarAction.setChecked(self._secondaryImageLayer.colorbarOn)
            self._rangeAction.setVisible(True)

    def __getitem__(self, item):
        return self._actions[item]

    def __len__(self):
        return len(self._actions)