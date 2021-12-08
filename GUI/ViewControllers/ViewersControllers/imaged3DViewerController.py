import numpy as np
from PyQt5.QtCore import pyqtSignal

from Controllers.DataControllers.image3DController import Image3DController


class Image3DViewerController(Image3DController):
    wwlChangedSignal = pyqtSignal(tuple)
    selectedPositionChangedSignal = pyqtSignal(tuple)

    def __init__(self, image):
        super().__init__(image)

        if hasattr(self, '_wwlValue'):
            return

        self._wwlValue = (400, 0)
        # TODO: Not a huge fan of this. Data controller should provide getOrigin, etc.
        self._selectedPosition = np.array(self.data.origin) + np.array(self.data.getGridSize())*np.array(self.data.spacing)/2.0

    def getSelectedPosition(self):
        return self._selectedPosition

    def getWWLValue(self):
        return self._wwlValue

    def setSelectedPosition(self, position):
        self._selectedPosition = (position[0], position[1], position[2])
        self.selectedPositionChangedSignal.emit(self._selectedPosition)

    def setWWLValue(self, wwl):
        if (wwl[0]==self._wwlValue[0]) and (wwl[1]==self._wwlValue[1]):
            return

        self._wwlValue = (wwl[0], wwl[1])
        self.wwlChangedSignal.emit(self._wwlValue)
