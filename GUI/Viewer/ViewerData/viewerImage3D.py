import numpy as np

from Core.event import Event
from GUI.Viewer.ViewerData.viewerData import ViewerData


class ViewerImage3D(ViewerData):
    def __init__(self, image):
        super().__init__(image)

        if hasattr(self, '_wwlValue'):
            return

        self.wwlChangedSignal = Event(tuple)
        self.selectedPositionChangedSignal = Event(tuple)

        self._wwlValue = (400, 0)
        # TODO: Not a huge fan of this. Data controller should provide getOrigin, etc.
        self._selectedPosition = np.array(self.data.origin) + np.array(self.data.gridSize) * np.array(self.data.spacing) / 2.0

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

    @property
    def selectedPosition(self):
        return self._selectedPosition

    @selectedPosition.setter
    def selectedPosition(self, position):
        self._selectedPosition = (position[0], position[1], position[2])
        self.selectedPositionChangedSignal.emit(self._selectedPosition)

    @property
    def wwlValue(self):
        return self._wwlValue

    @wwlValue.setter
    def wwlValue(self, wwl):
        if (wwl[0]==self._wwlValue[0]) and (wwl[1]==self._wwlValue[1]):
            return

        self._wwlValue = (wwl[0], wwl[1])
        self.wwlChangedSignal.emit(self._wwlValue)
