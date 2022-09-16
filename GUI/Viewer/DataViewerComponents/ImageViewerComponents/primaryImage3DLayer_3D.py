from typing import Optional, Sequence

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingCore as vtkRenderingCore
from vtkmodules import vtkRenderingVolume
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction

from Core.event import Event
from GUI.Viewer.DataForViewer.genericImageForViewer import GenericImageForViewer
from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer


class PrimaryImage3DLayer_3D:
    def __init__(self, renderer, renderWindow, iStyle):
        self.imageChangedSignal = Event(object)

        self._image = None
        self._imageToBeSet = None
        self._iStyle = iStyle
        self._mainActor = vtkRenderingCore.vtkVolume()
        self._mainMapper = vtkRenderingVolume.vtkFixedPointVolumeRayCastMapper()
        self._volumeColor = vtkRenderingCore.vtkColorTransferFunction()
        self._volumeScalarOpacity = vtkPiecewiseFunction()
        self._volumeGradientOpacity = vtkPiecewiseFunction()
        self._renderer = renderer
        self._renderWindow = renderWindow

        self._volumeColor.AddRGBPoint(-1000, 0.0, 0.0, 0.0)
        self._volumeColor.AddRGBPoint(-500, 240.0 / 255.0, 184.0 / 255.0, 160.0 / 255.0)
        self._volumeColor.AddRGBPoint(0, 240.0 / 255.0, 184.0 / 255.0, 160.0 / 255.0)
        self._volumeColor.AddRGBPoint(500, 1.0, 1.0, 240.0 / 255.0)

        self._volumeScalarOpacity.AddPoint(-1000, 0.00)
        self._volumeScalarOpacity.AddPoint(-500, 0.15)
        self._volumeScalarOpacity.AddPoint(0, 0.15)
        self._volumeScalarOpacity.AddPoint(500, 0.85)

        self._volumeGradientOpacity.AddPoint(-1000, 0.0)
        self._volumeGradientOpacity.AddPoint(0, 0.5)
        self._volumeGradientOpacity.AddPoint(100, 1.0)

        self._volumeProperty = vtkRenderingCore.vtkVolumeProperty()
        self._volumeProperty.SetColor(self._volumeColor)
        self._volumeProperty.SetScalarOpacity(self._volumeScalarOpacity)
        self._volumeProperty.SetGradientOpacity(self._volumeGradientOpacity)
        self._volumeProperty.SetInterpolationTypeToLinear()
        self._volumeProperty.ShadeOn()
        self._volumeProperty.SetAmbient(0.4)
        self._volumeProperty.SetDiffuse(0.6)
        self._volumeProperty.SetSpecular(0.2)

        self._mainActor.SetMapper(self._mainMapper)
        self._mainActor.SetProperty(self._volumeProperty)

        self.update()

    def close(self):
        self._disconnectAll()

    def update(self):
        self._setImage(self._imageToBeSet)

    @property
    def image(self) -> Optional[Image3DForViewer]:
        """
        Image displayed
        :type:Optional[Image3DForViewer]
        """
        if self._image is None:
            return None

        return self._image

    @image.setter
    def image(self, image:Optional[GenericImageForViewer]):
        if image == self._image:
            return

        if not (isinstance(image, GenericImageForViewer) or (image is None)):
            return

        self._imageToBeSet = image

    def _setImage(self, image:Optional[GenericImageForViewer]):
        self._image = image

        self._disconnectAll()
        self._renderer.RemoveActor(self._mainActor)
        self._mainMapper.RemoveAllInputs()

        if not (self._image is None):
            self._mainMapper.SetInputConnection(self._image.vtkOutputPort)

            self._renderer.AddActor(self._mainActor)

            self._connectAll()

        self.imageChangedSignal.emit(self._image)

        self._renderWindow.Render()

    def _setLookupTable(self):
        imageProperty = self._mainActor.GetProperty()
        imageProperty.SetLookupTable(self._image.lookupTable)
        imageProperty.UseLookupTableScalarRangeOn()

    def _updateLookupTable(self, lt):
        imageProperty = self._mainActor.GetProperty()
        imageProperty.SetLookupTable(self._image.lookupTable)

        self._renderWindow.Render()


    def _connectAll(self):
        self._image.dataChangedSignal.connect(self._render)
        self._image.lookupTableChangedSignal.connect(self._updateLookupTable)
        self._image.rangeChangedSignal.connect(self._render)

    def _disconnectAll(self):
        if self._image is None:
            return

        self._image.dataChangedSignal.disconnect(self._render)
        self._image.lookupTableChangedSignal.disconnect(self._updateLookupTable)
        self._image.rangeChangedSignal.connect(self._render)

    def _render(self, *args):
        self._renderWindow.Render()
