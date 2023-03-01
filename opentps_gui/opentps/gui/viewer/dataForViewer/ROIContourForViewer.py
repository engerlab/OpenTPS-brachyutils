from vtkmodules.vtkIOImage import vtkImageImport

from opentps.core.data.images._image3D import Image3D
from opentps.core import Event
from opentps.gui.viewer.dataForViewer.ROIMaskForViewer import ROIMaskForViewer
from opentps.gui.viewer.dataForViewer.dataMultiton import DataMultiton


class ROIContourForViewer(DataMultiton):
    def __init__(self, roiContour):
        super().__init__(roiContour)

        if hasattr(self, '_dataImporter'):
            return

        self.visibleChangedSignal = Event(bool)

        self._dataImporter = vtkImageImport()
        self._referenceImage = None
        self._visible = False
        self._vtkOutputPort = None
        self._mask = None

        self.colorChangedSignal.connect(self._updateMask)

        self._updateMask()

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

    @property
    def referenceImage(self) -> Image3D:
        return self._referenceImage

    @referenceImage.setter
    def referenceImage(self, image: Image3D):
        if image==self._referenceImage:
            return

        self._referenceImage = image
        self._updateMask()

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, visible: bool):
        self._visible = visible

        if not(self._mask is None):
            self._mask.visible = visible

        self.visibleChangedSignal.emit(self._visible)

    def asROIMaskForViewer(self) -> ROIMaskForViewer:
        return ROIMaskForViewer(self._mask)

    def _updateMask(self):
        if self._referenceImage is None:
            self._mask = None
            return

        referenceShape = self.referenceImage.gridSize
        referenceOrigin = self.referenceImage.origin
        referenceSpacing = self.referenceImage.spacing

        mask = self.getBinaryMask(origin=referenceOrigin, gridSize=referenceShape, spacing=referenceSpacing)

        if self._mask is None:
            self._mask = mask
        else:
            self._mask.color = mask.color
            self._mask.imageArray = mask.imageArray
            self._mask.origin = mask.origin
            self._mask.spacing = mask.spacing
            self._mask.name = mask.name

    @property
    def vtkOutputPort(self):
        if self._mask is None:
            return None

        return self.asROIMaskForViewer().vtkOutputPort
