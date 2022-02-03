from typing import Sequence, Optional

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingCore as vtkRenderingCore
from vtkmodules import vtkImagingCore, vtkCommonMath
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget, vtkScalarBarWidget
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper

from Core.event import Event
from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer


class SecondaryImageLayer:
    def __init__(self, renderer, renderWindow, iStyle):

        self.colorbarVisibilitySignal = Event(bool)
        self.imageChangedSignal = Event(object)

        self._color = vtkImagingCore.vtkImageMapToColors()
        self._colorbarActor = vtkScalarBarActor()
        self._colorbarWidget = vtkScalarBarWidget()
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

        self._colorbarActor.SetNumberOfLabels(5)
        self._colorbarActor.SetOrientationToVertical()
        self._colorbarActor.SetVisibility(False)
        self._colorbarActor.SetUnconstrainedFontSize(14)
        self._colorbarActor.SetMaximumWidthInPixels(20)

        self._colorbarWidget.SetInteractor(self._renderWindow.GetInteractor())
        self._colorbarWidget.SetScalarBarActor(self._colorbarActor)

        self._reslice.SetOutputDimensionality(2)
        self._reslice.SetInterpolationModeToNearestNeighbor()

    @property
    def image(self) -> Optional[Image3DForViewer]:
        if self._image is None:
            return None

        return self._image

    @image.setter
    def image(self, image: Optional[Image3DForViewer]):
        if image is None:
            self._reslice.RemoveAllInputs()
            self.colorbarOn = False
            self._disconnectAll()
            self._image = None
            self._mainActor.SetVisibility(False)
            self._renderWindow.Render()
            return

        if image == self._image:
            return

        self._disconnectAll()

        self._image = image

        self._color.SetLookupTable(self._image.lookupTable)
        self._colorbarActor.SetLookupTable(self._image.lookupTable)

        self._reslice.SetInputConnection(self._image.vtkOutputPort)
        self._renderer.AddActor(self._mainActor)
        self._color.SetInputConnection(self._reslice.GetOutputPort())
        self._mainMapper.SetInputConnection(self._color.GetOutputPort())

        self._mainActor.SetVisibility(True)

        self._connectAll()

        self.colorbarOn = True # TODO: Get this from parent

        self.imageChangedSignal.emit(self.image)

    @property
    def resliceAxes(self):
        return self._reslice.GetResliceAxes()

    @resliceAxes.setter
    def resliceAxes(self, resliceAxes):
        self._reslice.SetResliceAxes(resliceAxes)
        self._orientationActor.PokeMatrix(resliceAxes)

    @property
    def colorbarOn(self) -> bool:
        return self._colorbarActor.GetVisibility()

    @colorbarOn.setter
    def colorbarOn(self, visible: bool):
        if self._image is None:
            return

        if visible==self._colorbarActor.GetVisibility():
            return

        if visible:
            self._colorbarActor.SetVisibility(True)
            self._colorbarWidget.On()
        else:
            self._colorbarActor.SetVisibility(False)
            self._colorbarWidget.Off()

        self.colorbarVisibilitySignal.emit(visible)

        self._renderWindow.Render()

    def getDataAtPosition(self, position: Sequence):
        imageData = self._reslice.GetInput(0)
        ind = [0, 0, 0]
        imageData.TransformPhysicalPointToContinuousIndex(position[0:3], ind)
        data = imageData.GetScalarComponentAsFloat(round(ind[0]), round(ind[1]), round(ind[2]), 0)

        return data

    def _connectAll(self):
        self._image.lookupTableChangedSignal.connect(self._setLookupTable)

    def _disconnectAll(self):
        if self._image is None:
            return

        self._image.lookupTableChangedSignal.disconnect(self._setLookupTable)

    def _setLookupTable(self, lookuptable):
        self._color.SetLookupTable(lookuptable)
        self._colorbarActor.SetLookupTable(lookuptable)
        self._renderWindow.Render()
