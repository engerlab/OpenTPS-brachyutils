from typing import Optional

import vtkmodules.vtkRenderingCore as vtkRenderingCore
from vtkmodules import vtkCommonMath
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkIOGeometry import vtkSTLReader
import vtk

from opentps.core import Event
from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer
from opentps.gui.viewer.dataForViewer.image3DForViewer import Image3DForViewer


class PrimaryImage2DLayer:
    def __init__(self, renderer, renderWindow, iStyle):
        self.imageChangedSignal = Event(object)

        colors = vtkNamedColors()

        self._image = None
        self._iStyle = iStyle
        self._mainMapper = vtk.vtkImageMapper()
        self._mainActor = vtkRenderingCore.vtkActor2D()
        self._mainActor.SetMapper(self._mainMapper)
        # self._mainMapper = self._mainActor.GetMapper()
        # print('in PrimaryImage2DLayer init', self._mainMapper)
        # self._orientationActor = vtkActor()
        # self._orientationMapper = vtkDataSetMapper()
        # self._orientationWidget = vtkOrientationMarkerWidget()
        self._renderer = renderer
        self._renderWindow = renderWindow
        # self._reslice = vtkImagingCore.vtkImageReslice()
        self._stlReader = vtkSTLReader()
        self._viewMatrix = vtkCommonMath.vtkMatrix4x4()

        # self._mainMapper.SetSliceAtFocalPoint(True)

        # self._orientationActor.SetMapper(self._orientationMapper)
        # self._orientationActor.GetProperty().SetColor(colors.GetColor3d("Silver"))
        # self._orientationMapper.SetInputConnection(self._stlReader.GetOutputPort())
        # self._orientationWidget.SetViewport(0.8, 0.0, 1.0, 0.2)
        # self._orientationWidget.SetCurrentRenderer(self._renderer)
        # self._orientationWidget.SetInteractor(self._renderWindow.GetInteractor())
        # self._orientationWidget.SetOrientationMarker(self._orientationActor)

        # self._reslice.SetOutputDimensionality(2)
        # self._reslice.SetInterpolationModeToNearestNeighbor()

        self._setMainMapperInputConnection()

    def _setMainMapperInputConnection(self):
        if not (self._image is None):
            self._mainMapper.SetInputConnection(self._image.vtkOutputPort)
        # print('in primaryImage2DLayer, setMainMapperInputCOnnection')
        # print(type(self._image))

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
    def image(self, image:Optional[GenericImageForViewer]):
        self._setImage(image)

    def _setImage(self, image:Optional[GenericImageForViewer]):
        if image == self._image:
            return

        if not (isinstance(image, GenericImageForViewer) or (image is None)):
            return

        self._image = image

        self._disconnectAll()
        self._renderer.RemoveActor(self._mainActor)
        # self._reslice.RemoveAllInputs()

        if not (self._image is None):
            # self._reslice.SetInputConnection(self._image.vtkOutputPort)

            self._renderer.AddActor(self._mainActor)

            self._image.lookupTableName = 'gray'
            # self._setLookupTable()

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
        self._image.lookupTableChangedSignal.connect(self._updateLookupTable)
        self._image.rangeChangedSignal.connect(self._render)

    def _disconnectAll(self):
        if self._image is None:
            return

        self._image.lookupTableChangedSignal.disconnect(self._updateLookupTable)
        self._image.rangeChangedSignal.connect(self._render)

    def _render(self, *args):
        self._renderWindow.Render()

    def resliceDataFromPhysicalPoint(self, point):
        imageData = self._reslice.GetInput(0)

        ind = [0, 0, 0]
        imageData.TransformPhysicalPointToContinuousIndex(point, ind)
        return imageData.GetScalarComponentAsFloat(int(ind[0]), int(ind[1]), int(ind[2]), 0)
