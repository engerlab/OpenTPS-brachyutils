import numpy as np
from vtkmodules.vtkIOImage import vtkImageImport

from Core.event import Event
from GUI.Viewer.DataForViewer.dataForViewer import DataForViewer
from GUI.Viewer.Viewers.lookupTables import LookupTables


class Image3DForViewer(DataForViewer):
    def __init__(self, image):
        super().__init__(image)

        if hasattr(self, '_wwlValue'):
            return

        self.wwlChangedSignal = Event(tuple)
        self.lookupTableChangedSignal = Event(object)
        self.selectedPositionChangedSignal = Event(tuple)

        self._dataImporter = vtkImageImport()
        self._wwlValue = (400, 0)
        self._lookupTableName = 'fusion'
        self._range = (-1024, 1500)
        self._opacity = 0.5
        self._lookupTable = LookupTables()[self._lookupTableName](self._range, self._opacity)
        self._selectedPosition = np.array(self.data.origin) + np.array(self.data.gridSize) * np.array(self.data.spacing) / 2.0
        self._vtkOutputPort = None

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

    @property
    def vtkOutputPort(self):
        if self._vtkOutputPort is None:
            shape = self.gridSize
            imageOrigin = self.origin
            imageSpacing = self.spacing
            imageData = np.swapaxes(self.imageArray, 0, 2)
            num_array = np.array(np.ravel(imageData), dtype=np.float32)

            self._dataImporter.SetNumberOfScalarComponents(1)
            self._dataImporter.SetDataExtent(0, shape[0] - 1, 0, shape[1] - 1, 0, shape[2] - 1)
            self._dataImporter.SetWholeExtent(0, shape[0] - 1, 0, shape[1] - 1, 0, shape[2] - 1)
            self._dataImporter.SetDataSpacing(imageSpacing[0], imageSpacing[1], imageSpacing[2])
            self._dataImporter.SetDataOrigin(imageOrigin[0], imageOrigin[1], imageOrigin[2])
            self._dataImporter.SetDataScalarTypeToFloat()

            data_string = num_array.tobytes()
            self._dataImporter.CopyImportVoidPointer(data_string, len(data_string))

            self._vtkOutputPort = self._dataImporter.GetOutputPort()

        return self._vtkOutputPort
