from typing import Optional, Sequence

from vtkmodules import vtkImagingCore
from vtkmodules.vtkInteractionWidgets import vtkScalarBarWidget
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor

from opentps.core import Event
from opentps.gui.viewer.dataForViewer.image3DForViewer import Image3DForViewer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.primaryImage3DLayer import PrimaryImage3DLayer


class SecondaryImage3DLayer(PrimaryImage3DLayer):
    def __init__(self, renderer, renderWindow, iStyle):
        self._colorMapper = vtkImagingCore.vtkImageMapToColors()

        super().__init__(renderer, renderWindow, iStyle)

        self.colorbarVisibilitySignal = Event(bool)
        self.lookupTableChangedSignal = Event(bool)

        self._colorbarActor = vtkScalarBarActor()
        self._colorbarWidget = vtkScalarBarWidget()

        self._colorbarActor.SetNumberOfLabels(5)
        self._colorbarActor.SetOrientationToVertical()
        self._colorbarActor.SetVisibility(False)
        self._colorbarActor.SetUnconstrainedFontSize(14)
        self._colorbarActor.SetMaximumWidthInPixels(20)

        self._colorbarWidget.SetInteractor(self._renderWindow.GetInteractor())
        self._colorbarWidget.SetScalarBarActor(self._colorbarActor)

    def _setMainMapperInputConnection(self):
        self._colorMapper.SetInputConnection(self._reslice.GetOutputPort())
        self._mainMapper.SetInputConnection(self._colorMapper.GetOutputPort())

    def close(self):
        super().close()

    def _setImage(self, image: Optional[Image3DForViewer]):
        if image == self._image:
            return

        super()._setImage(image)

        if image is None:
            self.colorbarOn = False
        else:
            self._image.lookupTableName = 'jet'
            self.colorbarOn = True # TODO: Get this from parent

        self._renderWindow.Render()

    @property
    def colorbarOn(self) -> bool:
        """
        Colorbar visibility
        :type: bool
        """
        return self._colorbarActor.GetVisibility()

    @colorbarOn.setter
    def colorbarOn(self, visible: bool):
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

    def _connectAll(self):
        super()._connectAll()

    def _disconnectAll(self):
        super()._disconnectAll()

        if self._image is None:
            return

    def _setLookupTable(self):
        self._updateLookupTable(self._image.lookupTable)

    def _updateLookupTable(self, lt):
        self._colorMapper.SetLookupTable(lt)
        self._colorbarActor.SetLookupTable(lt)

        self._renderWindow.Render()

    def _setWWL(self, wwl: Sequence):
        # WWL is changed via iStyle. It is only working on the primary image.
        pass
