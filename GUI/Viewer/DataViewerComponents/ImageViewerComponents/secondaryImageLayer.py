from typing import Sequence, Optional

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
from vtkmodules.vtkInteractionWidgets import vtkScalarBarWidget
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor

from Core.event import Event
from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer
from GUI.Viewer.DataViewerComponents.ImageViewerComponents.primaryImageLayer import PrimaryImageLayer


class SecondaryImageLayer(PrimaryImageLayer):
    def __init__(self, renderer, renderWindow, iStyle):
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

    def _setImage(self, image: Optional[Image3DForViewer]):
        if image == self._image:
            return

        super()._setImage(image)

        if image is None:
            self.colorbarOn = False
        else:
            self._setLookupTable(self._image.lookupTable)
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
        self._image.lookupTableChangedSignal.connect(self._setLookupTable)

    def _disconnectAll(self):
        if self._image is None:
            return

        self._image.lookupTableChangedSignal.disconnect(self._setLookupTable)

    def _setLookupTable(self, lookupTable):
        self._colorMapper.SetLookupTable(lookupTable)
        self._colorbarActor.SetLookupTable(lookupTable)
        self._renderWindow.Render()
