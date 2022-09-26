import numpy as np
from vtkmodules.vtkIOImage import vtkImageImport

from opentps.core import Event
from opentps.gui.viewer.dataForViewer.dataMultiton import DataMultiton


class ROIMaskForViewer(DataMultiton):
    def __init__(self, roiContour):
        super().__init__(roiContour)

        if hasattr(self, '_visible'):
            return

        self.visibleChangedSignal = Event(bool)

        self._dataImporter = vtkImageImport()
        self._visible = False
        self._vtkOutputPort = None

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

    def _updateVtkOutputPort(self):
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
