
import typing

import numpy as np

from Core.event import Event

from GUI.Viewer.DataForViewer.dataMultiton import DataMultiton
from GUI.Viewer.DataViewerComponents.ImageViewerComponents.lookupTables import LookupTables


class GenericImageForViewer(DataMultiton):

    def __init__(self, image):
        super().__init__(image)

        if hasattr(self, '_wwlValue'):
            return

        self.wwlChangedSignal = Event(tuple)
        self.lookupTableChangedSignal = Event(object)
        self.selectedPositionChangedSignal = Event(tuple)
        self.rangeChangedSignal = Event(tuple)

        self._wwlValue = (400, 0)
        self._lookupTableName = 'fusion'
        self._range = (np.min(self.data.imageArray), np.max(self.data.imageArray))
        self._opacity = 0.5
        self._lookupTable = LookupTables()[self._lookupTableName](self._range, self._opacity)
        self._selectedPosition = (0, 0, 0)
        self._vtkOutputPort = None

    @property
    def selectedPosition(self) -> tuple:
        return self._selectedPosition

    @selectedPosition.setter
    def selectedPosition(self, position: typing.Sequence):
        self._selectedPosition = (position[0], position[1], position[2])
        self.selectedPositionChangedSignal.emit(self._selectedPosition)

    @property
    def wwlValue(self) -> tuple:
        return self._wwlValue

    @wwlValue.setter
    def wwlValue(self, wwl: typing.Sequence):
        if (wwl[0]==self._wwlValue[0]) and (wwl[1]==self._wwlValue[1]):
            return

        self._wwlValue = (wwl[0], wwl[1])
        self.wwlChangedSignal.emit(self._wwlValue)

    @property
    def lookupTable(self):
        return self._lookupTable

    @lookupTable.setter
    def lookupTable(self, lookupTableName):
        self._lookupTable = LookupTables()[lookupTableName](self.range,self.opacity)
        self.lookupTableChangedSignal.emit(self._lookupTable)

    @property
    def range(self) -> tuple:
        return self._range

    @range.setter
    def range(self, range: typing.Sequence):
        if range[0]==self._range[0] and range[1]==self._range[1]:
            return

        self._range = (range[0], range[1])
        self.lookupTable = self._lookupTableName

        self.rangeChangedSignal.emit(self._range)

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, opacity: float):
        self._opacity = opacity
        self.lookupTable = self._lookupTableName

    @property
    def vtkOutputPort(self):
        raise NotImplementedError()
