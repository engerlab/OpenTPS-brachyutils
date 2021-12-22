import numpy as np
from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.roiContourController import ROIContourController


class ROIContourViewerController(ROIContourController):
    visibleChangedSignal = pyqtSignal(bool)

    def __init__(self, image):
        super().__init__(image)

        if hasattr(self, '_wwlValue'):
            return

        self._visible = True

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

    def getVisible(self):
        return self._visible

    def setVisible(self, visible):
        self._visible = visible
        self.visibleChangedSignal.emit(self._visible)
