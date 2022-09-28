import numpy as np
from vtkmodules.vtkIOImage import vtkImageImport

from opentps.core.data.images._image3D import Image3D
from opentps.core import Event
from opentps.gui.viewer.dataForViewer.dataMultiton import DataMultiton


class ROIContourForViewer(DataMultiton):
    def __init__(self, roiContour):
        super().__init__(roiContour)

        if hasattr(self, '_visible'):
            return

        self.visibleChangedSignal = Event(bool)

        self._dataImporter = vtkImageImport()
        self._referenceImage = None
        self._visible = False
        self._vtkOutputPort = None

        self._updateVtkOutputPort()

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

    @property
    def referenceImage(self) -> Image3D:
        return self._referenceImage

    @referenceImage.setter
    def referenceImage(self, image: Image3D):
        self._referenceImage = image
        self._updateVtkOutputPort()

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, visible: bool):
        self._visible = visible
        self.visibleChangedSignal.emit(self._visible)

    def _updateVtkOutputPort(self):
        if self._referenceImage is None:
            return

        referenceShape = self.referenceImage.gridSize
        referenceOrigin = self.referenceImage.origin
        referenceSpacing = self.referenceImage.spacing

        mask = self.getBinaryMask(origin=referenceOrigin, gridSize=referenceShape,
                                           spacing=referenceSpacing)
        maskData = mask._imageArray
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
