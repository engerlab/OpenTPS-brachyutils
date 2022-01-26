import numpy as np
from vtkmodules.vtkIOImage import vtkImageImport

from Core.event import Event
from GUI.Viewer.DataForViewer.dataMultiton import DataMultiton
from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer
from GUI.Viewer.Viewers.lookupTables import LookupTables


class Dyn3DSeqForViewer(DataMultiton):
    def __init__(self, dyn3DSeq):
        super().__init__(dyn3DSeq)

        if hasattr(self, '_wwlValue'):
            return

        self.dyn3DSeq = dyn3DSeq

        self.wwlChangedSignal = Event(tuple)
        self.lookupTableChangedSignal = Event(object)
        self.selectedPositionChangedSignal = Event(tuple)

        self._wwlValue = (400, 0)
        self._lookupTableName = 'fusion'
        self._range = (-1024, 1500)
        self._opacity = 0.5
        self._lookupTable = LookupTables()[self._lookupTableName](self._range, self._opacity)
        self._selectedPosition = np.array(dyn3DSeq.dyn3DImageList[0].origin) + np.array(dyn3DSeq.dyn3DImageList[0].gridSize) * np.array(dyn3DSeq.dyn3DImageList[0].spacing) / 2.0
        self.isOver = False

        self._dataImporter = vtkImageImport()
        self._vtkOutputPort = None
        self.image3DForViewerList = self.getImg3DForViewerList(dyn3DSeq.dyn3DImageList)


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

    @property
    def lookupTable(self):
        return self._lookupTable

    @lookupTable.setter
    def lookupTable(self, lookupTableName):
        self._lookupTable = LookupTables()[lookupTableName](self.range,self.opacity)
        self.lookupTableChangedSignal.emit(self._lookupTable)

    @property
    def range(self):
        return self._range

    @range.setter
    def range(self, range):
        self._range = (range[0], range[1])
        self.lookupTable = self._lookupTableName

    @property
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, opacity):
        self._opacity = opacity
        self.lookupTable = self._lookupTableName

    def getImg3DForViewerList(self, dyn3DSeqImgList):

        vtkImageList = []
        for image in dyn3DSeqImgList:
            vtkImageList.append(Image3DForViewer(image))

        return vtkImageList

