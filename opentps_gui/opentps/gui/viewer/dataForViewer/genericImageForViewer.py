
import typing
from math import isclose

from opentps.core import Event

from opentps.gui.viewer.dataForViewer.dataMultiton import DataMultiton
import opentps.gui.viewer.dataViewerComponents.imageViewerComponents.lookupTables as lookupTables


class GenericImageForViewer(DataMultiton):
    def __init__(self, image):
        super().__init__(image)

        if hasattr(self, '_wwlValue'):
            return

        self.wwlChangedSignal = Event(tuple)
        self.lookupTableChangedSignal = Event(object)
        self.selectedPositionChangedSignal = Event(tuple)
        self.rangeChangedSignal = Event(tuple)

        self._range = (-500, 500)
        self._wwlValue = (self._range[1]-self._range[0], (self._range[1]+self._range[0])/2.)
        self._lookupTableName = 'gray'
        self._opacity = 0.5
        self._selectedPosition = (0, 0, 0)
        self._vtkOutputPort = None

        self._updateLT()

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
        if isclose(wwl[0], self._wwlValue[0], abs_tol=0.1) and isclose(wwl[1], self._wwlValue[1], abs_tol=0.1):
            return

        self._wwlValue = (wwl[0], wwl[1])
        self.range = (wwl[1]-wwl[0]/2., wwl[1]+wwl[0]/2.)
        self.wwlChangedSignal.emit(self._wwlValue)

    @property
    def lookupTable(self) :
        return self._lookupTable

    @property
    def lookupTableName(self) -> str:
        return self._lookupTableName

    @lookupTableName.setter
    def lookupTableName(self, lookupTableName:str):
        if self._lookupTableName == lookupTableName:
            return

        self._lookupTableName = lookupTableName
        self._updateLT()

    def _updateLT(self):
        if self._lookupTableName == 'gray':
            self._lookupTable = lookupTables.grayLT(self._range)
        else:
            self._lookupTable = lookupTables.fusionLT(self._range, self._opacity, self._lookupTableName)
        self.lookupTableChangedSignal.emit(self._lookupTable)

    @property
    def range(self) -> tuple:
        return self._range

    @range.setter
    def range(self, range: typing.Sequence):
        if isclose(range[0], self._range[0], abs_tol=0.1) and isclose(range[1], self._range[1], abs_tol=0.1):
            return

        self._range = (range[0], range[1])
        self.wwlValue = (range[1]-range[0], (range[1]+range[0])/2.)

        if not (self._lookupTable is None) and self._lookupTableName=='gray':
            self._lookupTable.SetRange(self._range[0], self._range[1])
        else:
            self._updateLT()

        self.rangeChangedSignal.emit(self._range)

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, opacity: float):
        self._opacity = opacity
        self._updateLT()

    @property
    def vtkOutputPort(self):
        raise NotImplementedError()
