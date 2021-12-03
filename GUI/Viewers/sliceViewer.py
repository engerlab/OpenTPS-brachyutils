from PyQt5.QtWidgets import *
import numpy as np

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingCore as vtkRenderingCore
import vtkmodules.vtkCommonCore as vtkCommonCore
import vtkmodules.vtkInteractionStyle as vtkInteractionStyle
from vtkmodules import vtkImagingCore, vtkCommonMath
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkIOImage import vtkImageImport
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor, vtkCoordinate, vtkTextActor

from GUI.ViewControllers.ViewersControllers.imaged3DViewerController import Image3DViewerController


class SliceViewerVTK(QWidget):

  def __init__(self, controller):
    QWidget.__init__(self)

    self._controller = controller
    self._controller.mainImageChangeSignal.connect(self.setMainImage)
    self._controller.contourAddedSignal.connect(self.setNewContour)

    self._mainImageController = None
    self.contourReslices = []
    self.contourList = []
    self.__sendingWWL = False

    self.viewMatrix = vtkCommonMath.vtkMatrix4x4()
    self.leftButtonPress = False

    self.mainLayout = QVBoxLayout()
    self.vtkWidget = QVTKRenderWindowInteractor(self)

    self.setLayout(self.mainLayout)
    self.mainLayout.addWidget(self.vtkWidget)
    self.mainLayout.setContentsMargins(0, 0, 0, 0)

    #self.textOverlay = Overlay(self.vtkWidget)
    #self.textOverlay.show()

    self.renderer = vtkRenderingCore.vtkRenderer()
    self.renderWindow = self.vtkWidget.GetRenderWindow()
    self.reslice = vtkImagingCore.vtkImageReslice()
    self.mainActor = vtkRenderingCore.vtkImageActor()
    self.mainMapper = self.mainActor.GetMapper()
    self.iStyle = vtkInteractionStyle.vtkInteractorStyleImage()

    self.dataImporter = vtkImageImport()


    self.renderer.SetBackground(0, 0, 0)
    self.renderer.ResetCamera()
    self.renderer.AddActor(self.mainActor)

    self.mainText = ['', '', '', '']
    self.TextActor = vtkTextActor()
    self.TextActor.GetTextProperty().SetFontSize(14)
    self.TextActor.GetTextProperty().SetColor(1, 0.5, 0)
    self.TextActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
    self.TextActor.SetPosition(0.05, 0.05)
    self.renderer.AddActor(self.TextActor)

    self.renderWindow.AddRenderer(self.renderer)

    self.reslice.SetOutputDimensionality(2)
    self.reslice.SetInterpolationModeToNearestNeighbor()

    self.mainMapper.SetSliceAtFocalPoint(True)

    self.iStyle.SetInteractionModeToImageSlicing()

    self.iStyle.AddObserver("MouseWheelForwardEvent", self._scrollCallback)
    self.iStyle.AddObserver("MouseWheelBackwardEvent", self._scrollCallback)

    self.iStyle.AddObserver("MouseMoveEvent", self.mouseMoveCallback)
    self.iStyle.AddObserver("LeftButtonPressEvent", self._leftButtonCallback)
    self.iStyle.AddObserver("LeftButtonReleaseEvent", self._leftButtonCallback)

    self.renderWindow.GetInteractor().SetInteractorStyle(self.iStyle)

    self.setView('axial')

  #overrides QWidget resizeEvent
  def resizeEvent(self, event):
    QWidget.resizeEvent(self, event)

    if not (self._mainImageController is None):
      self.renderWindow.Render()
    #todo Trigger a reslice of QVTKRenderWindowInteractor

  def _connectAll(self):
    self._mainImageController.nameChangedSignal.connect(self.updateName)

  def _disconnectAll(self):
    if self._mainImageController is None:
      return

    self._mainImageController.nameChangedSignal.disconnect(self.updateName)
    self._mainImageController.wwlChangedSignal.disconnect(self.setWWL)
    self._mainImageController.selectedPositionChangedSignal.disconnect(self.setPosition)

  def _leftButtonCallback(self, obj, event):
    if 'Press' in event:
      self.leftButtonPress = True
      if self._controller.isCrossHairEnabled():
        self.mouseMoveCallback(None, None)
      else:
        self.iStyle.OnLeftButtonDown()
    else:
      self.leftButtonPress = False
      self.iStyle.OnLeftButtonUp()

  def getResliceMatrix(self):
    return self.reslice.GetResliceAxes()

  def mouseMoveCallback(self, obj, event):
    (mouseX, mouseY) = self.renderWindow.GetInteractor().GetEventPosition()

    # MouseX and MouseY are not related to image but to renderWindow
    dPos = vtkCoordinate()
    dPos.SetCoordinateSystemToDisplay()
    dPos.SetValue(mouseX, mouseY, 0)
    worldPos = dPos.GetComputedWorldValue(self.renderer)

    matrix = self.reslice.GetResliceAxes()
    point = matrix.MultiplyPoint((worldPos[0], worldPos[1], 0, 1))

    self.updateCurrentPosition(point)

    if self.leftButtonPress and self._controller.isCrossHairEnabled():
      self._mainImageController.setSelectedPosition(point)
    else:
      self.iStyle.OnMouseMove()

      if self.leftButtonPress and self._controller.isWWLEnabled():
        self.__sendingWWL = True
        imageProperty = self.iStyle.GetCurrentImageProperty()
        self._mainImageController.setWWLValue((imageProperty.GetColorWindow(), imageProperty.GetColorLevel()))
        self.__sendingWWL = False

  def setPosition(self, position):
    if self._mainImageController is None:
      return

    transfo_mat = vtkCommonMath.vtkMatrix4x4()
    transfo_mat.DeepCopy(self.viewMatrix)
    transfo_mat.Invert()
    pos = transfo_mat.MultiplyPoint((position[0], position[1], position[2], 1))
    pos = self.viewMatrix.MultiplyPoint((0, 0, pos[2], 1))

    self.reslice.Update()
    matrix = self.reslice.GetResliceAxes()
    matrix.SetElement(0, 3, pos[0])
    matrix.SetElement(1, 3, pos[1])
    matrix.SetElement(2, 3, pos[2])

    for reslice in self.contourReslices:
      reslice.Update()
      reslice.SetResliceAxes(matrix)

    self.renderWindow.Render()

    self.updateCurrentPosition(position)

  def setWWL(self, wwl):
    if self._mainImageController is None:
      return

    if self.__sendingWWL:
      return

    imageProperty = self.iStyle.GetCurrentImageProperty()
    if not (imageProperty is None):
      imageProperty.SetColorWindow(wwl[0])
      imageProperty.SetColorLevel(wwl[1])

    self.renderWindow.Render()

  def setResliceMatrix(self, resliceMatrix):
    self.reslice.SetResliceAxes(resliceMatrix)

    for reslice in self.contourReslices:
      reslice.Update()
      reslice.SetResliceAxes(resliceMatrix)

    self.renderWindow.Render()

  def setView(self, viewName):
    axial = vtkCommonMath.vtkMatrix4x4()
    axial.DeepCopy((0, 0, 1, 0,
                    0, -1, 0, 0,
                    1, 0, 0, 0,
                    0, 0, 0, 1))

    coronal = vtkCommonMath.vtkMatrix4x4()
    coronal.DeepCopy((0, 1, 0, 0,
                       1, 0, 0, 0,
                       0, 0, -1, 0,
                       0, 0, 0, 1))

    sagittal = vtkCommonMath.vtkMatrix4x4()
    sagittal.DeepCopy((0, 1, 0, 0,
                      0, 0, -1, 0,
                      1, 0, 0, 0,
                      0, 0, 0, 1))

    if viewName=='sagittal':
      resliceAxes = sagittal
      self.viewMatrix.DeepCopy(sagittal)
    if viewName=='axial':
      resliceAxes = axial
      self.viewMatrix.DeepCopy(axial)
    if viewName=='coronal':
      resliceAxes = coronal
      self.viewMatrix.DeepCopy(coronal)

    self.reslice.SetResliceAxes(resliceAxes)
    for reslice in self.contourReslices:
      reslice.SetResliceAxes(resliceAxes)

  def setMainImage(self, imageController):
    self._disconnectAll()

    if imageController is None:
      self.reslice.RemoveAllInputs()
      self._mainImageController = None
      return

    self._mainImageController = Image3DViewerController(imageController)
    self._mainImageController.wwlChangedSignal.connect(self.setWWL)
    self._mainImageController.selectedPositionChangedSignal.connect(self.setPosition)

    image = self._mainImageController.data

    shape = image.getGridSize()
    imageData = image.data
    imageOrigin = image.origin
    imageSpacing = image.spacing
    #imageData = np.swapaxes(imageData, 0, 1)
    num_array = np.array(np.ravel(imageData), dtype=np.float32)

    self.dataImporter.SetNumberOfScalarComponents(1)
    self.dataImporter.SetDataExtent(0, shape[2]-1, 0, shape[1]-1, 0, shape[0]-1)
    self.dataImporter.SetWholeExtent(0, shape[2]-1, 0, shape[1]-1, 0, shape[0]-1)
    self.dataImporter.SetDataSpacing(imageSpacing[2], imageSpacing[1], imageSpacing[0])
    self.dataImporter.SetDataOrigin(imageOrigin[2], imageOrigin[1], imageOrigin[0])
    self.dataImporter.SetDataScalarTypeToFloat()

    data_string = num_array.tobytes()
    self.dataImporter.CopyImportVoidPointer(data_string , len(data_string))

    self.reslice.SetInputConnection(self.dataImporter.GetOutputPort())

    # Create a greyscale lookup table
    table = vtkCommonCore.vtkLookupTable()
    table.SetRange(-1024, 1500)  # image intensity range
    table.SetValueRange(0.0, 1.0)  # from black to white
    table.SetSaturationRange(0.0, 0.0)  # no color saturation
    table.SetRampToLinear()
    table.Build()

    # Map the image through the lookup table
    color = vtkImagingCore.vtkImageMapToColors()
    color.SetLookupTable(table)
    color.SetInputConnection(self.reslice.GetOutputPort())

    self.mainMapper.SetInputConnection(color.GetOutputPort())

    # Start interaction
    self.renderWindow.GetInteractor().Start()

    #Trick to instantiate image property in iStyle
    self.iStyle.EndWindowLevel()
    self.iStyle.OnLeftButtonDown()
    self.iStyle.WindowLevel()
    self.renderWindow.GetInteractor().SetEventPosition(400, 0)
    self.iStyle.InvokeEvent(vtkCommand.StartWindowLevelEvent)
    self.iStyle.OnLeftButtonUp()
    self.iStyle.EndWindowLevel()

    if self._controller.isWWLEnabled():
      self.iStyle.StartWindowLevel()
      self.iStyle.OnLeftButtonUp()


    self.iStyle.SetCurrentImageNumber(0)

    self._connectAll()

    self.updateName()

  def setNewContour(self, contourController):
    if self._mainImageController is None:
      return

    image = self._mainImageController.data
    imageShape = image.getGridSize()
    imageOrigin = image.origin
    imageSpacing = image.spacing

    vtkContourObj = vtkContour(contourController, self.renderWindow)
    vtkContourObj.build(imageOrigin, imageSpacing, imageShape)

    self.renderer.AddActor(vtkContourObj.getActor())
    self.contourReslices.append(vtkContourObj.getReslice())

    self.contourList.append(vtkContourObj)

    matrix = self.reslice.GetResliceAxes()
    vtkContourObj.getReslice().SetResliceAxes(matrix)

    self.renderWindow.Render()

  def _scrollCallback(self, obj, event):
    sliceSpacing = self.reslice.GetOutput().spacing[2]

    if 'Forward' in event:
      deltaY = sliceSpacing
    if 'Backward' in event:
      deltaY = -sliceSpacing

    self.reslice.Update()
    matrix = self.reslice.GetResliceAxes()
    # move the center point that we are slicing through
    center = matrix.MultiplyPoint((0, 0, deltaY, 1))
    matrix.SetElement(0, 3, center[0])
    matrix.SetElement(1, 3, center[1])
    matrix.SetElement(2, 3, center[2])

    self.setResliceMatrix(matrix)

    if self._controller.isCrossHairEnabled():
      worldPos = self._mainImageController.getSelectedPosition()
      if worldPos is None:
        return

      matrix = self.reslice.GetResliceAxes()
      tform = vtkCommonMath.vtkMatrix4x4()
      tform.DeepCopy(matrix)
      tform.Invert()
      point = tform.MultiplyPoint((worldPos[0], worldPos[1], worldPos[2], 1))

      point = matrix.MultiplyPoint((point[0], point[1], point[2]+deltaY, 1))

      self._mainImageController.setSelectedPosition(point)

  def updateCurrentPosition(self, position):
    try:
      imageData = self.reslice.GetInput(0)
      ind = [0, 0, 0]
      imageData.TransformPhysicalPointToContinuousIndex(position[0:3], ind)
      data = imageData.GetScalarComponentAsFloat(int(ind[0]), int(ind[1]), int(ind[2]), 0)
      self.mainText[0] = 'Value: ' + str(data)
    except:
      self.mainText[0] = ''

    self.renderOverlay()

  def updateName(self):
    self.mainText[1] = self._mainImageController.getName()
    self.renderOverlay()

  def renderOverlay(self):
    self.TextActor.SetInput(self.mainText[0] + '\n' + self.mainText[1])
    self.renderWindow.Render()


class vtkContour:
  def __init__(self, contourController, renderWindow):
    #TODO: disconnect contours
    self._contourController = contourController
    self._contourController.getVisibleChangeSignal().connect(self.setVisible)
    self._contourController.getColorChangeSignal().connect(self.reloadColor)

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

  def build(self, referenceOrigin, referenceSpacing, referenceShape):
    image, _ = self._contourController.getMask(referenceOrigin, referenceShape, referenceSpacing)
    imageData = image.data
    num_array = np.array(np.ravel(imageData), dtype=np.float32)

    dataImporter = vtkImageImport()
    dataImporter.SetNumberOfScalarComponents(1)
    dataImporter.SetDataScalarTypeToFloat()

    dataImporter.SetDataExtent(0, referenceShape[2] - 1, 0, referenceShape[1] - 1, 0, referenceShape[0] - 1)
    dataImporter.SetWholeExtent(0, referenceShape[2] - 1, 0, referenceShape[1] - 1, 0, referenceShape[0] - 1)
    dataImporter.SetDataSpacing(referenceSpacing[2], referenceSpacing[1], referenceSpacing[0])
    dataImporter.SetDataOrigin(referenceOrigin[2], referenceOrigin[1], referenceOrigin[0])

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
