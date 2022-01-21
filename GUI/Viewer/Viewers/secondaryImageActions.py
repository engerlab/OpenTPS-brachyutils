import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction

from GUI.Viewer.Viewers.imageFusionProperties import ImageFusionProperties


class SecondaryImageActions:
    def __init__(self, image):
        self._actions = []

        iconPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'icons' + os.path.sep
        action = QAction(QIcon(iconPath + "color-adjustment.png"), "Range")
        action.setStatusTip("Range")
        action.triggered.connect(lambda pressed: ImageFusionProperties(image).show())

        # TODO action to hide colorbar

        self._actions.append(action)

    def __getitem__(self, item):
        return self._actions[item]

    def __len__(self):
        return len(self._actions)