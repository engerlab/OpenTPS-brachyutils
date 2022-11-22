from functools import partial
from typing import Optional, Union, Sequence

from vtkmodules import vtkImagingCore, vtkCommonCore
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images import ROIMask
from opentps.core.data._roiContour import ROIContour
from opentps.gui.viewer.dataForViewer.ROIContourForViewer import ROIContourForViewer
from opentps.gui.viewer.dataForViewer.ROIMaskForViewer import ROIMaskForViewer


class ContourLayer:
    def __init__(self, renderer, renderWindow):
        self._contours = [] # Acts as a cache
        self._referenceImage = None
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._resliceAxes = None
        self._vtkContours = []
        self._partialHandlers = []

    def close(self):
        for vtkContour in self._vtkContours:
            vtkContour.close()

    @property
    def contours(self) -> Sequence[Union[ROIContourForViewer, ROIMaskForViewer]]:
        return [contour for contour in self._contours]

    def setNewContour(self, contour:Union[ROIContour, ROIMask]):
        if isinstance(contour, ROIContour):
            contour = ROIContourForViewer(contour)
        elif isinstance(contour, ROIMask):
            contour = ROIMaskForViewer(contour)
        else:
            raise ValueError(str(type(contour)) + ' is not a valid type for a contour.')

        if contour in self._contours:
            return

        if not contour.visible:
            return

        contour.referenceImage = self.referenceImage

        self._contours.append(contour)

        vtkContourObj = vtkContour(contour, self._renderWindow)

        self._renderer.AddActor(vtkContourObj.actor)
        vtkContourObj.resliceAxes = self._resliceAxes
        self._vtkContours.append(vtkContourObj)

        partialHandler = partial(self._handleVisibilityChange, contour)
        self._partialHandlers.append(partialHandler)
        contour.visibleChangedSignal.connect(partialHandler)

        self._renderWindow.Render()

    def _handleVisibilityChange(self, contour:Union[ROIContourForViewer, ROIMaskForViewer], visible):
        if not contour.visible:
            self._removeContour(contour)

    def _removeContour(self, contour:Union[ROIContourForViewer, ROIMaskForViewer]):
        contourIndex = self._contours.index(contour)
        vtkContourObj = self._vtkContours[contourIndex]
        partialHandler = self._partialHandlers[contourIndex]
        self._renderer.RemoveActor(vtkContourObj.actor)

        self._contours.remove(contour)
        self._vtkContours.remove(vtkContourObj)
        self._partialHandlers.remove(partialHandler)

        contour.visibleChangedSignal.disconnect(partialHandler)


    @property
    def referenceImage(self) -> Optional[Image3D]:
        return self._referenceImage

    @referenceImage.setter
    def referenceImage(self, image: Image3D):
        self._referenceImage = image

        for contour in self._contours:
            contour.referenceImage = self._referenceImage

    @property
    def resliceAxes(self):
        return self._resliceAxes

    @resliceAxes.setter
    def resliceAxes(self, resliceAxes):
        self._resliceAxes = resliceAxes
        self._updateContoursResliceAxes()

    def _updateContoursResliceAxes(self):
        for vtkContour in self._vtkContours:
            vtkContour.resliceAxes = self._resliceAxes

    def resliceDataFromPhysicalPoint(self, point):
        return [contour.resliceDataFromPhysicalPoint(point) for contour in self._vtkContours]

class vtkContour:
    def __init__(self, contour, renderWindow):
        self.actor = vtkActor()
        self._contour = contour
        self.contourFilter = vtkContourFilter()
        self.mapper = vtkPolyDataMapper()
        self.renderWindow = renderWindow  # Not very beautiful to pass renderWindow but fewer lines of code than trigering a render event
        self.reslice = vtkImagingCore.vtkImageReslice()

        self.actor.SetMapper(self.mapper)

        self.reslice.SetOutputDimensionality(2)
        self.reslice.SetInterpolationModeToNearestNeighbor()

        self.reslice.SetInputConnection(self._contour.vtkOutputPort)
        self.contourFilter.SetInputConnection(self.reslice.GetOutputPort())
        self.mapper.SetInputConnection(self.contourFilter.GetOutputPort())

        self.contourFilter.SetValue(0, 0.1)
        self.contourFilter.Update()

        self.actor.GetProperty().SetLineWidth(3)

        self.reloadColor()

        self.setVisible(self._contour.visible)

        self._contour.visibleChangedSignal.connect(self.setVisible)
        self._contour.colorChangedSignal.connect(self.reloadColor)

    def close(self):
        self._contour.visibleChangedSignal.disconnect(self.setVisible)
        self._contour.colorChangedSignal.disconnect(self.reloadColor)

    @property
    def resliceAxes(self):
        return self.reslice.GetResliceAxes()

    @resliceAxes.setter
    def resliceAxes(self, resliceAxes):
        self.reslice.SetResliceAxes(resliceAxes)

    def reloadColor(self):
        imageColor = self._contour.color

        # Create a greyscale lookup table
        table = vtkCommonCore.vtkLookupTable()
        table.SetRange(0, 1)  # image intensity range
        table.SetValueRange(0.0, 1.0)  # from black to white
        table.SetSaturationRange(0.0, 0.0)  # no color saturation
        table.SetRampToLinear()

        table.SetNumberOfTableValues(2)
        table.SetTableValue(0, (imageColor[0] / 255.0, imageColor[1] / 255.0, imageColor[2] / 255.0, 1))
        table.SetTableValue(1, (imageColor[0] / 255.0, imageColor[1] / 255.0, imageColor[2] / 255.0, 1))
        table.SetBelowRangeColor(0, 0, 0, 0)
        table.SetUseBelowRangeColor(True)
        table.SetAboveRangeColor(imageColor[0] / 255.0, imageColor[1] / 255.0, imageColor[2] / 255.0, 1)
        table.SetUseAboveRangeColor(True)
        table.Build()

        # contourActor.GetProperty().SetColor(imageColor[0], imageColor[1], imageColor[2])
        self.mapper.SetLookupTable(table)

    def setVisible(self, visible: bool):
        self.actor.SetVisibility(visible)
        self.renderWindow.Render()

    def resliceDataFromPhysicalPoint(self, point):
        imageData = self.reslice.GetInput(0)

        ind = [0, 0, 0]
        imageData.TransformPhysicalPointToContinuousIndex(point, ind)
        return imageData.GetScalarComponentAsFloat(int(ind[0]), int(ind[1]), int(ind[2]), 0)
