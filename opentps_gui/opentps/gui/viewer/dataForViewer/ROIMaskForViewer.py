import numpy as np
from vtkmodules.vtkIOImage import vtkImageImport

from opentps.core import Event
from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents import lookupTables


class ROIMaskForViewer(GenericImageForViewer):
    def __init__(self, roiContour):
        super().__init__(roiContour)

        if hasattr(self, '_dataImporter'):
            return

        self.visibleChangedSignal = Event(bool)

        self._dataImporter = vtkImageImport()
        self._visible = False
        self._vtkOutputPort = None

        self.colorChangedSignal.connect(self._updateLT)

        self._updateVtkOutputPort()

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, visible: bool):
        self._visible = visible
        self.visibleChangedSignal.emit(self._visible)

    def _updateLT(self, *args):
        self._lookupTable = lookupTables.uniqueColorLT(1., 0.8, [self.color[0]/255, self.color[1]/255, self.color[2]/255])
        self.lookupTableChangedSignal.emit(self._lookupTable)

    def _updateVtkOutputPort(self):
        if self._imageArray is None:
            return
        referenceShape = self.gridSize
        referenceOrigin = self.origin
        referenceSpacing = self.spacing

        maskData = self._imageArray
        maskData = np.swapaxes(maskData, 0, 2)
        num_array = np.array(np.ravel(maskData), dtype=np.float32)

        self._dataImporter.SetNumberOfScalarComponents(1)
        self._dataImporter.SetDataScalarTypeToFloat()

        self._dataImporter.SetDataExtent(0, referenceShape[0] - 1, 0, referenceShape[1] - 1, 0, referenceShape[2] - 1)
        self._dataImporter.SetWholeExtent(0, referenceShape[0] - 1, 0, referenceShape[1] - 1, 0, referenceShape[2] - 1)
        self._dataImporter.SetDataSpacing(referenceSpacing[0], referenceSpacing[1], referenceSpacing[2])
        self._dataImporter.SetDataOrigin(referenceOrigin[0], referenceOrigin[1], referenceOrigin[2])

        data_string = num_array.tobytes()
        self._dataImporter.CopyImportVoidPointer(data_string, len(data_string))

        self._vtkOutputPort = self._dataImporter.GetOutputPort()

    @property
    def vtkOutputPort(self):
        return self._vtkOutputPort
