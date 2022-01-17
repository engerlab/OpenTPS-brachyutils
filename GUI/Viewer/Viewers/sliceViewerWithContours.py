import numpy as np

import vtkmodules.vtkCommonCore as vtkCommonCore
from vtkmodules import vtkImagingCore
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkIOImage import vtkImageImport
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

from GUI.Viewer.ViewerData.viewerROIContour import ViewerROIContour
from GUI.Viewer.Viewers.sliceViewerWithFusion import SliceViewerWithFusion


class SliceViewerWithContours(SliceViewerWithFusion):

  def __init__(self, viewController):
    SliceViewerWithFusion.__init__(self, viewController)

    self._contours = []
    self._vtkContours = []
    self._contourReslices = []


    self._viewController.showContourSignal.connect(self._setNewContour)

  def _setNewContour(self, contour):
    contour = ViewerROIContour(contour)

    if self._mainImage is None:
      return

    if contour in self._contours:
      return

    self._contours.append(contour)

    vtkContourObj = vtkContour(contour, self._renderWindow)
    vtkContourObj.build(self._mainImage)

    self._renderer.AddActor(vtkContourObj.getActor())
    self._contourReslices.append(vtkContourObj.getReslice())
    self._vtkContours.append(vtkContourObj)

    matrix = self._reslice.GetResliceAxes()
    vtkContourObj.getReslice().SetResliceAxes(matrix)

    self._renderWindow.Render()


class vtkContour:
  def __init__(self, contour, renderWindow):
    #TODO: disconnect contours
    self._contour = contour
    self._contour.visibleChangedSignal.connect(self.setVisible)
    self._contour.colorChangedSignal.connect(self.reloadColor)

    self.renderWindow = renderWindow #Not very beautiful to pass renderWindow but fewer lines of code than trigering a render event

    self.mapper = vtkPolyDataMapper()
    self.actor = vtkActor()
    self.reslice = None

    self.actor.SetMapper(self.mapper)

  def getActor(self):
    return self.actor

  def getReslice(self):
    return self.reslice

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

  def build(self, referenceImage):
    referenceShape = referenceImage.gridSize
    referenceOrigin = referenceImage.origin
    referenceSpacing = referenceImage.spacing

    mask = self._contour.getBinaryMask(origin=referenceOrigin, gridSize=referenceShape, spacing=referenceSpacing)
    maskData = mask._imageArray
    maskData = np.swapaxes(maskData, 0, 2)
    num_array = np.array(np.ravel(maskData), dtype=np.float32)

    dataImporter = vtkImageImport()
    dataImporter.SetNumberOfScalarComponents(1)
    dataImporter.SetDataScalarTypeToFloat()

    dataImporter.SetDataExtent(0, referenceShape[0] - 1, 0, referenceShape[1] - 1, 0, referenceShape[2] - 1)
    dataImporter.SetWholeExtent(0, referenceShape[0] - 1, 0, referenceShape[1] - 1, 0, referenceShape[2] - 1)
    dataImporter.SetDataSpacing(referenceSpacing[0], referenceSpacing[1], referenceSpacing[2])
    dataImporter.SetDataOrigin(referenceOrigin[0], referenceOrigin[1], referenceOrigin[2])

    data_string = num_array.tobytes()
    dataImporter.CopyImportVoidPointer(data_string, len(data_string))

    self.reslice = vtkImagingCore.vtkImageReslice()
    self.reslice.SetOutputDimensionality(2)
    self.reslice.SetInterpolationModeToNearestNeighbor()

    contourFilter = vtkContourFilter()

    self.reslice.SetInputConnection(dataImporter.GetOutputPort())
    contourFilter.SetInputConnection(self.reslice.GetOutputPort())
    self.mapper.SetInputConnection(contourFilter.GetOutputPort())

    contourFilter.SetValue(0, 0.1)
    contourFilter.Update()

    self.actor.GetProperty().SetLineWidth(3)

    self.reloadColor()

  def setVisible(self, visible):
    self.actor.SetVisibility(visible)

    self.renderWindow.Render()
