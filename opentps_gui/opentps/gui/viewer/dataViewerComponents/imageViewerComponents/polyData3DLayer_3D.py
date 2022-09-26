from typing import Optional

from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

from opentps.core import Event
from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer
from opentps.gui.viewer.dataForViewer.image3DForViewer import Image3DForViewer


class PolyData3DLayer_3D:
    def __init__(self, renderer, renderWindow):
        self.imageChangedSignal = Event(object)

        self._image = None
        self._imageToBeSet = None
        self._renderer = renderer
        self._renderWindow = renderWindow

        self._mainActor = vtkActor()
        self._mainMapper = vtkPolyDataMapper()
        self._mainActor.SetMapper(self._mainMapper)

    def close(self):
        self._disconnectAll()
        self._renderer.RemoveActor(self._mainActor)
        self._mainMapper.RemoveAllInputs()

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

            colors = vtkNamedColors()
            #backFaceProp = vtkProperty()
            #backFaceProp.SetDiffuseColor(colors.GetColor3d("Silver"))
            #self._mainActor.SetBackfaceProperty(backFaceProp)
            self._mainActor.GetProperty().SetDiffuseColor(colors.GetColor3d("NavajoWhite"))

            self._connectAll()

        self.imageChangedSignal.emit(self._image)

        self._renderWindow.Render()


    def _connectAll(self):
        self._image.dataChangedSignal.connect(self._render)

    def _disconnectAll(self):
        if self._image is None:
            return

        self._image.dataChangedSignal.disconnect(self._render)

    def _render(self, *args):
        self._renderWindow.Render()
