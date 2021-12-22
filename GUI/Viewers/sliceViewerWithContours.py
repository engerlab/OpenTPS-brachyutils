import numpy as np

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkCommonCore as vtkCommonCore
from vtkmodules import vtkImagingCore, vtkCommonMath
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkIOImage import vtkImageImport
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

from GUI.Viewers.sliceViewer import SliceViewerVTK


class SliceViewerWithContour(SliceViewerVTK):

  def __init__(self, viewController):
    SliceViewerVTK.__init__(self, viewController)

    self.contourControllerList = []
    self.contourList = []
    self.contourReslices = []


    self._viewController.showContourSignal.connect(self.setNewContour)

  def setNewContour(self, contourController):
    if self._mainImageController is None:
      return

    if contourController in self.contourControllerList:
      return

    self.contourControllerList.append(contourController)

    vtkContourObj = vtkContour(contourController, self._renderWindow)
    vtkContourObj.build(self._mainImageController.data)

    self._renderer.AddActor(vtkContourObj.getActor())
    self.contourReslices.append(vtkContourObj.getReslice())
    self.contourList.append(vtkContourObj)

    matrix = self._reslice.GetResliceAxes()
    vtkContourObj.getReslice().SetResliceAxes(matrix)

    self._renderWindow.Render()


class vtkContour:
  def __init__(self, contourController, renderWindow):
    #TODO: disconnect contours
    self._contourController = contourController
    self._contourController.visibleChangedSignal.connect(self.setVisible)
    self._contourController.colorChangedSignal.connect(self.reloadColor)

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
    imageColor = self._contourController.getColor()

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
    referenceShape = referenceImage.getGridSize()
    referenceOrigin = referenceImage.origin
    referenceSpacing = referenceImage.spacing

    mask = self._contourController.getBinaryMask(referenceImage)
    maskData = mask.data
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
