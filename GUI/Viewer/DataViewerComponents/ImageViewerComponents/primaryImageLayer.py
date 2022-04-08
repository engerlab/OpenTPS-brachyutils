from typing import Optional, Sequence

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingCore as vtkRenderingCore
import vtkmodules.vtkCommonCore as vtkCommonCore
from vtkmodules import vtkImagingCore, vtkCommonMath
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper

from Core.event import Event
from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer


class PrimaryImageLayer:
    def __init__(self, renderer, renderWindow, iStyle):
        self.imageChangedSignal = Event(object)

        colors = vtkNamedColors()

        self._colorMapper = vtkImagingCore.vtkImageMapToColors()
        self._image = None
        self._iStyle = iStyle
        self._mainActor = vtkRenderingCore.vtkImageActor()
        self._mainMapper = self._mainActor.GetMapper()
        self._orientationActor = vtkActor()
        self._orientationMapper = vtkDataSetMapper()
        self._orientationWidget = vtkOrientationMarkerWidget()
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._reslice = vtkImagingCore.vtkImageReslice()
        self._stlReader = vtkSTLReader()
        self._viewMatrix = vtkCommonMath.vtkMatrix4x4()

        self._mainMapper.SetSliceAtFocalPoint(True)

        self._orientationActor.SetMapper(self._orientationMapper)
        self._orientationActor.GetProperty().SetColor(colors.GetColor3d("Silver"))
        self._orientationMapper.SetInputConnection(self._stlReader.GetOutputPort())
        self._orientationWidget.SetViewport(0.8, 0.0, 1.0, 0.2)
        self._orientationWidget.SetCurrentRenderer(self._renderer)
        self._orientationWidget.SetInteractor(self._renderWindow.GetInteractor())
        self._orientationWidget.SetOrientationMarker(self._orientationActor)

        self._reslice.SetOutputDimensionality(2)
        self._reslice.SetInterpolationModeToNearestNeighbor()

        self._colorMapper.SetInputConnection(self._reslice.GetOutputPort())
        self._mainMapper.SetInputConnection(self._colorMapper.GetOutputPort())

    def close(self):
        self._disconnectAll()

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
    def image(self, image:Optional[Image3DForViewer]):
        self._setImage(image)

    def _setImage(self, image:Optional[Image3DForViewer]):
        if image == self._image:
            return

        if not (isinstance(image, Image3DForViewer) or (image is None)):
            return

        self._image = image

        self._disconnectAll()
        self._renderer.RemoveActor(self._mainActor)
        self._reslice.RemoveAllInputs()

        if not (self._image is None):
            self._reslice.SetInputConnection(self._image.vtkOutputPort)

            self._setInitialGrayRange(self._image.range)
            self._setWWL(self._image.wwlValue)

            self._connectAll()

            self._renderer.AddActor(self._mainActor)

        self.imageChangedSignal.emit(self._image)

        self._renderWindow.Render()

    def _setInitialGrayRange(self, range:tuple):
        """
        Set grayscale range
        Parameters
        ----------
        range(tuple): range
        """
        table = vtkCommonCore.vtkLookupTable()
        table.SetRange(range[0], range[1])  # image intensity range
        table.SetValueRange(0.0, 1.0)  # from black to white
        table.SetSaturationRange(0.0, 0.0)  # no color saturation
        table.SetRampToLinear()
        table.Build()

        self._colorMapper.SetLookupTable(table)

    @property
    def resliceAxes(self):
        """
        Reslice axes
        """
        return self._reslice.GetResliceAxes()

    @resliceAxes.setter
    def resliceAxes(self, resliceAxes):
        self._reslice.SetResliceAxes(resliceAxes)
        self._orientationActor.PokeMatrix(resliceAxes)

    def _connectAll(self):
        self._image.wwlChangedSignal.connect(self._setWWL)

    def _disconnectAll(self):
        if self._image is None:
            return

        self._image.wwlChangedSignal.disconnect(self._setWWL)

    def _setWWL(self, wwl: Sequence):
        """
            Set window level
            Parameters
             ----------
            range(Sequence): (window width, window level)
        """
        imageProperty = self._iStyle.GetCurrentImageProperty()
        if not (imageProperty is None):
            imageProperty.SetColorWindow(wwl[0])
            imageProperty.SetColorLevel(wwl[1])

            self._renderWindow.Render()

    def _resliceDataFromPhysicalPoint(self, point):
        imageData = self._reslice.GetInput(0)

        ind = [0, 0, 0]
        imageData.TransformPhysicalPointToContinuousIndex(point, ind)
        return imageData.GetScalarComponentAsFloat(int(ind[0]), int(ind[1]), int(ind[2]), 0)
