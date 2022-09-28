
import numpy as np
from vtkmodules.vtkIOImage import vtkImageImport

from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer


class Image3DForViewer(GenericImageForViewer):

    def __init__(self, image):
        super().__init__(image)

        if hasattr(self, '_dataImporter'):
            return

        self._dataImporter = vtkImageImport()
        self._selectedPosition = self.data.origin + self.data.gridSizeInWorldUnit/2.
        self._range = (np.min(self.data.imageArray), np.max(self.data.imageArray))

        self.data.dataChangedSignal.connect(self._updateVTKOutputPort)
        self._updateVTKOutputPort()

    def _updateVTKOutputPort(self):
        shape = self.gridSize  ## dataMultiton magic makes all this available here
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

    @property
    def vtkOutputPort(self):
        return self._vtkOutputPort
