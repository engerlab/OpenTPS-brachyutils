from typing import Optional

import vtkmodules.vtkRenderingCore as vtkRenderingCore
from vtkmodules.vtkRenderingVolumeOpenGL2 import vtkSmartVolumeMapper

from opentps.core import Event
from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer
from opentps.gui.viewer.dataForViewer.image3DForViewer import Image3DForViewer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.lookupTables import ct3DLT


class PrimaryImage3DLayer_3D:
    def __init__(self, renderer, renderWindow, iStyle):
        self.imageChangedSignal = Event(object)

        self._image = None
        self._imageToBeSet = None
        self._iStyle = iStyle
        self._mainActor = vtkRenderingCore.vtkVolume()
        self._mainMapper = vtkSmartVolumeMapper()
        self._renderer = renderer
        self._renderWindow = renderWindow

        self._mainActor.SetMapper(self._mainMapper)

        self._volumeColor, self._volumeScalarOpacity, self._volumeGradientOpacity = ct3DLT()

        self._volumeProperty = vtkRenderingCore.vtkVolumeProperty()
        self._volumeProperty.SetColor(self._volumeColor)
        self._volumeProperty.SetScalarOpacity(self._volumeScalarOpacity)
        self._volumeProperty.SetGradientOpacity(self._volumeGradientOpacity)
        self._volumeProperty.SetInterpolationTypeToLinear()
        self._volumeProperty.ShadeOn()
        self._volumeProperty.SetAmbient(0.4)
        self._volumeProperty.SetDiffuse(0.6)
        self._volumeProperty.SetSpecular(0.2)

    def close(self):
        self._disconnectAll()
        self._renderer.RemoveActor(self._mainActor)
        self._mainMapper.RemoveAllInputs()

    def update(self):
        self._setImage(self._imageToBeSet)

    @property
    def image(self) -> Optional[Image3DForViewer]:
        return self._imageToBeSet

    @image.setter
    def image(self, image:Optional[GenericImageForViewer]):
        if image == self._imageToBeSet:
            return

        self._imageToBeSet = image

    def _setImage(self, image:Optional[GenericImageForViewer]):
        if self._image == self._imageToBeSet:
            return

        self._image = image

        self._disconnectAll()
        self._renderer.RemoveActor(self._mainActor)
        self._mainMapper.RemoveAllInputs()

        if not (self._image is None):
            self._mainMapper.SetInputConnection(self._image.vtkOutputPort)

            self._renderer.AddActor(self._mainActor)

            self._mainActor.SetProperty(self._volumeProperty)

            self._connectAll()

            self._renderer.ResetCamera()

        self.imageChangedSignal.emit(self._image)

        self._renderWindow.Render()

    def _connectAll(self):
        self._image.dataChangedSignal.connect(self._render)
        self._image.lookupTableChangedSignal.connect(self._updateLookupTable)

    def _disconnectAll(self):
        if self._image is None:
            return

        self._image.dataChangedSignal.disconnect(self._render)
        self._image.lookupTableChangedSignal.disconnect(self._updateLookupTable)

    def _render(self, *args):
        self._renderWindow.Render()

    def _updateLookupTable(self, lt):
        pass
