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
from vtkmodules.vtkIOImage import vtkImageImport
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor, vtkCoordinate, vtkTextActor

from GUI.ViewControllers.ViewersControllers.imaged3DViewerController import Image3DViewerController


class SliceViewerVTK(QWidget):

  def __init__(self, viewerController):
    QWidget.__init__(self)

    self._dataImporter = vtkImageImport()
    self._iStyle = vtkInteractionStyle.vtkInteractorStyleImage()
    self._leftButtonPress = False
    self._mainImageController = None
    self._mainActor = vtkRenderingCore.vtkImageActor()
    self._mainLayout = QVBoxLayout()
    self._mainMapper = self._mainActor.GetMapper()
    self._mainText = ['', '', '', '']
    self._renderer = vtkRenderingCore.vtkRenderer()
    self._reslice = vtkImagingCore.vtkImageReslice()
    self.__sendingWWL = False
    self._textActor = vtkTextActor()
    self._viewerController = viewerController
    self._viewMatrix = vtkCommonMath.vtkMatrix4x4()
    self._vtkWidget = QVTKRenderWindowInteractor(self)

    self._renderWindow = self._vtkWidget.GetRenderWindow()

    self.setLayout(self._mainLayout)
    self._mainLayout.addWidget(self._vtkWidget)
    self._mainLayout.setContentsMargins(0, 0, 0, 0)

    self._textActor.GetTextProperty().SetFontSize(14)
    self._textActor.GetTextProperty().SetColor(1, 0.5, 0)
    self._textActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
    self._textActor.SetPosition(0.05, 0.05)

    self._renderer.SetBackground(0, 0, 0)
    self._renderer.ResetCamera()
    self._renderer.AddActor(self._mainActor)
    self._renderer.AddActor(self._textActor)

    self._renderWindow.AddRenderer(self._renderer)

    self._reslice.SetOutputDimensionality(2)
    self._reslice.SetInterpolationModeToNearestNeighbor()

    self._mainMapper.SetSliceAtFocalPoint(True)

    self._iStyle.SetInteractionModeToImageSlicing()

    self._iStyle.AddObserver("MouseWheelForwardEvent", self.onScroll)
    self._iStyle.AddObserver("MouseWheelBackwardEvent", self.onScroll)
    self._iStyle.AddObserver("MouseMoveEvent", self.onMouseMove)
    self._iStyle.AddObserver("LeftButtonPressEvent", self.onLeftButtonPressed)
    self._iStyle.AddObserver("LeftButtonReleaseEvent", self.onLeftButtonPressed)

    self._renderWindow.GetInteractor().SetInteractorStyle(self._iStyle)

    self.setView('axial')

    self._viewerController.mainImageChangeSignal.connect(self.setMainImage)

  #overrides QWidget resizeEvent
  def resizeEvent(self, event):
    QWidget.resizeEvent(self, event)

    if not (self._mainImageController is None):
      self._renderWindow.Render()
    #todo Trigger a reslice of QVTKRenderWindowInteractor

  def _connectAll(self):
    if self._mainImageController is None:
      return

    self._mainImageController.nameChangedSignal.connect(self.updateNameText)
    self._mainImageController.wwlChangedSignal.connect(self._setWWL)
    self._mainImageController.selectedPositionChangedSignal.connect(self._setPosition)

  def _disconnectAll(self):
    if self._mainImageController is None:
      return

    self._mainImageController.nameChangedSignal.disconnect(self.updateNameText)
    self._mainImageController.wwlChangedSignal.disconnect(self._setWWL)
    self._mainImageController.selectedPositionChangedSignal.disconnect(self._setPosition)

  def getResliceMatrix(self):
    return self._reslice.GetResliceAxes()

  def onLeftButtonPressed(self, obj=None, event='Press'):
    if 'Press' in event:
      self._leftButtonPress = True
      if self._viewerController.isCrossHairEnabled():
        self.onMouseMove(None, None)
      else:
        self._iStyle.OnLeftButtonDown()
    else:
      self._leftButtonPress = False
      self._iStyle.OnLeftButtonUp()

  def onMouseMove(self, obj=None, event=None):
    (mouseX, mouseY) = self._renderWindow.GetInteractor().GetEventPosition()

    # MouseX and MouseY are not related to image but to renderWindow
    dPos = vtkCoordinate()
    dPos.SetCoordinateSystemToDisplay()
    dPos.SetValue(mouseX, mouseY, 0)
    worldPos = dPos.GetComputedWorldValue(self._renderer)

    matrix = self._reslice.GetResliceAxes()
    point = matrix.MultiplyPoint((worldPos[0], worldPos[1], 0, 1))

    self._updateCurrentPositionText(point)

    if self._leftButtonPress and self._viewerController.isCrossHairEnabled():
      self._mainImageController.setSelectedPosition(point)
    else:
      self._iStyle.OnMouseMove()

      if self._leftButtonPress and self._viewerController.isWWLEnabled():
        self.__sendingWWL = True
        imageProperty = self._iStyle.GetCurrentImageProperty()
        self._mainImageController.setWWLValue((imageProperty.GetColorWindow(), imageProperty.GetColorLevel()))
        self.__sendingWWL = False

  def onScroll(self, obj=None, event='Forward'):
    sliceSpacing = self._reslice.GetOutput().spacing[2]

    if 'Forward' in event:
      deltaY = sliceSpacing
    if 'Backward' in event:
      deltaY = -sliceSpacing

    self._reslice.Update()
    matrix = self._reslice.GetResliceAxes()
    # move the center point that we are slicing through
    center = matrix.MultiplyPoint((0, 0, deltaY, 1))
    matrix.SetElement(0, 3, center[0])
    matrix.SetElement(1, 3, center[1])
    matrix.SetElement(2, 3, center[2])

    self._setResliceMatrix(matrix)

    if self._viewerController.isCrossHairEnabled():
      worldPos = self._mainImageController.getSelectedPosition()
      if worldPos is None:
        return

      matrix = self._reslice.GetResliceAxes()
      tform = vtkCommonMath.vtkMatrix4x4()
      tform.DeepCopy(matrix)
      tform.Invert()
      point = tform.MultiplyPoint((worldPos[0], worldPos[1], worldPos[2], 1))

      point = matrix.MultiplyPoint((point[0], point[1], point[2]+deltaY, 1))

      self._mainImageController.setSelectedPosition(point)

  def renderOverlay(self):
    self._textActor.SetInput(self._mainText[0] + '\n' + self._mainText[1])
    self._renderWindow.Render()

  def _setPosition(self, position):
    if self._mainImageController is None:
      return

    transfo_mat = vtkCommonMath.vtkMatrix4x4()
    transfo_mat.DeepCopy(self._viewMatrix)
    transfo_mat.Invert()
    pos = transfo_mat.MultiplyPoint((position[0], position[1], position[2], 1))
    pos = self._viewMatrix.MultiplyPoint((0, 0, pos[2], 1))

    self._reslice.Update()
    matrix = self._reslice.GetResliceAxes()
    matrix.SetElement(0, 3, pos[0])
    matrix.SetElement(1, 3, pos[1])
    matrix.SetElement(2, 3, pos[2])

    self._renderWindow.Render()

    self._updateCurrentPositionText(position)

  def _setResliceMatrix(self, resliceMatrix):
    self._reslice.SetResliceAxes(resliceMatrix)
    self._renderWindow.Render()

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
      self._viewMatrix.DeepCopy(sagittal)
    if viewName=='axial':
      resliceAxes = axial
      self._viewMatrix.DeepCopy(axial)
    if viewName=='coronal':
      resliceAxes = coronal
      self._viewMatrix.DeepCopy(coronal)

    self._reslice.SetResliceAxes(resliceAxes)

  def _setWWL(self, wwl):
    if self._mainImageController is None:
      return

    if self.__sendingWWL:
      return

    imageProperty = self._iStyle.GetCurrentImageProperty()
    if not (imageProperty is None):
      imageProperty.SetColorWindow(wwl[0])
      imageProperty.SetColorLevel(wwl[1])

    self._renderWindow.Render()

  def setMainImage(self, imageController):
    self._disconnectAll()

    if imageController is None:
      self._reslice.RemoveAllInputs()
      self._mainImageController = None
      return

    self._mainImageController = Image3DViewerController(imageController)

    image = self._mainImageController.data

    shape = image.getGridSize()
    imageData = image.data
    imageOrigin = image.origin
    imageSpacing = image.spacing
    #imageData = np.swapaxes(imageData, 0, 1)
    num_array = np.array(np.ravel(imageData), dtype=np.float32)

    self._dataImporter.SetNumberOfScalarComponents(1)
    self._dataImporter.SetDataExtent(0, shape[2] - 1, 0, shape[1] - 1, 0, shape[0] - 1)
    self._dataImporter.SetWholeExtent(0, shape[2] - 1, 0, shape[1] - 1, 0, shape[0] - 1)
    self._dataImporter.SetDataSpacing(imageSpacing[2], imageSpacing[1], imageSpacing[0])
    self._dataImporter.SetDataOrigin(imageOrigin[2], imageOrigin[1], imageOrigin[0])
    self._dataImporter.SetDataScalarTypeToFloat()

    data_string = num_array.tobytes()
    self._dataImporter.CopyImportVoidPointer(data_string, len(data_string))

    self._reslice.SetInputConnection(self._dataImporter.GetOutputPort())

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
    color.SetInputConnection(self._reslice.GetOutputPort())

    self._mainMapper.SetInputConnection(color.GetOutputPort())

    # Start interaction
    self._renderWindow.GetInteractor().Start()

    #Trick to instantiate image property in iStyle
    self._iStyle.EndWindowLevel()
    self._iStyle.OnLeftButtonDown()
    self._iStyle.WindowLevel()
    self._renderWindow.GetInteractor().SetEventPosition(400, 0)
    self._iStyle.InvokeEvent(vtkCommand.StartWindowLevelEvent)
    self._iStyle.OnLeftButtonUp()
    self._iStyle.EndWindowLevel()

    if self._viewerController.isWWLEnabled():
      self._iStyle.StartWindowLevel()
      self._iStyle.OnLeftButtonUp()

    self._iStyle.SetCurrentImageNumber(0)

    self._connectAll()

    self.updateNameText()

  def _updateCurrentPositionText(self, position):
    try:
      imageData = self._reslice.GetInput(0)
      ind = [0, 0, 0]
      imageData.TransformPhysicalPointToContinuousIndex(position[0:3], ind)
      data = imageData.GetScalarComponentAsFloat(int(ind[0]), int(ind[1]), int(ind[2]), 0)
      self._mainText[0] = 'Value: ' + str(data)
    except:
      self._mainText[0] = ''

    self.renderOverlay()

  def updateNameText(self):
    self._mainText[1] = self._mainImageController.getName()
    self.renderOverlay()
