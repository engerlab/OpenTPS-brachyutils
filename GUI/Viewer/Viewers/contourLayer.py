
import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
from vtkmodules import vtkImagingCore, vtkCommonCore
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from Core.Data.Images.image3D import Image3D
from Core.Data.roiContour import ROIContour
from GUI.Viewer.DataForViewer.ROIContourForViewer import ROIContourForViewer


class ContourLayer:
    def __init__(self, renderer, renderWindow):
        self._contours = [] # Acts as a cache
        self._referenceImage = None
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._resliceAxes = None
        self._vtkContours = []

    def setNewContour(self, contour: ROIContour):
        contour = ROIContourForViewer(contour)

        if contour in self._contours:
            return

        contour.referenceImage = self.referenceImage

        self._contours.append(contour)

        vtkContourObj = vtkContour(contour, self._renderWindow)

        self._renderer.AddActor(vtkContourObj.actor)
        vtkContourObj.resliceAxes = self._resliceAxes
        self._vtkContours.append(vtkContourObj)

        self._renderWindow.Render()

    @property
    def referenceImage(self) -> Image3D:
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
        for contour in self._contours:
            contour.resliceAxes = resliceAxes

        self._resliceAxes = resliceAxes

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

        # TODO: disconnect contours
        self._contour.visibleChangedSignal.connect(self.setVisible)
        self._contour.colorChangedSignal.connect(self.reloadColor)

    @property
    def resliceAxes(self):
        return self.reslice.GetResliceAxes()

    @resliceAxes.setter
    def resliceAxes(self, resliceAxes):
        if self.reslice is None:
            return
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
