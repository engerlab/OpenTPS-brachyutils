import os
from math import sqrt

from PyQt5.QtCore import pyqtSignal, QLocale
from PyQt5.QtWidgets import *
import numpy as np

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingCore as vtkRenderingCore
import vtkmodules.vtkCommonCore as vtkCommonCore
import vtkmodules.vtkInteractionStyle as vtkInteractionStyle
from vtkmodules import vtkImagingCore, vtkCommonMath
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkCommand, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyLine, vtkCellArray, vtkPolyData
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkIOImage import vtkImageImport
from vtkmodules.vtkInteractionWidgets import vtkLineWidget2, vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkRenderingCore import vtkCoordinate, vtkTextActor, vtkPolyDataMapper, vtkActor, vtkPropPicker, \
  vtkMapper, vtkDataSetMapper

from GUI.ViewControllers.ViewersControllers.imaged3DViewerController import Image3DViewerController
from GUI.Viewers.blackEmptyPlot import BlackEmptyPlot


class SliceViewerVTK(QWidget):
  crossHairEnabledSignal = pyqtSignal(bool)
  lineWidgeEnabledSignal = pyqtSignal(bool)
  wwlEnabledSignal = pyqtSignal(bool)
  wwlEnabledSignal = pyqtSignal(bool)

  def __init__(self):
    QWidget.__init__(self)

    self._blackWidget = BlackEmptyPlot()
    self._crossHairActor = vtkActor()
    self._crossHairEnabled = False
    self._crossHairMapper = vtkPolyDataMapper()
    self._dataImporter = vtkImageImport()
    self._iStyle = vtkInteractionStyle.vtkInteractorStyleImage()
    self._leftButtonPress = False
    self._lineWidget = vtkLineWidget2()
    self._lineWidgetCallback = None
    self._lineWidgetEnabled = False
    self._lineWidgetNoInteractionYet = False
    self._mainImageController = None
    self._mainActor = vtkRenderingCore.vtkImageActor()
    self._mainLayout = QVBoxLayout()
    self._mainMapper = self._mainActor.GetMapper()
    self._mainText = ['', '', '', '']
    self._renderer = vtkRenderingCore.vtkRenderer()
    self._reslice = vtkImagingCore.vtkImageReslice()
    self._rightButtonPress = False
    self.__sendingWWL = False
    self._textActor = vtkTextActor()
    self._viewMatrix = vtkCommonMath.vtkMatrix4x4()
    self._vtkWidget = QVTKRenderWindowInteractor(self)
    self._wwlEnabled = False

    self._renderWindow = self._vtkWidget.GetRenderWindow()

    self.setLayout(self._mainLayout)
    self._vtkWidget.hide()
    self._mainLayout.addWidget(self._blackWidget)
    self._blackWidget.show()
    self._mainLayout.setContentsMargins(0, 0, 0, 0)

    self._textActor.GetTextProperty().SetFontSize(14)
    self._textActor.GetTextProperty().SetColor(1, 0.5, 0)
    self._textActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
    self._textActor.SetPosition(0.05, 0.05)

    self._renderer.SetBackground(0, 0, 0)
    self._renderer.GetActiveCamera().SetParallelProjection(True)

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

    self._lineWidget.SetCurrentRenderer(self._renderer)

    self._crossHairActor.SetMapper(self._crossHairMapper)
    colors = vtkNamedColors()
    self._crossHairActor.GetProperty().SetColor(colors.GetColor3d('Tomato'))
    self._renderer.AddActor(self._crossHairActor)

    self._stlReader = vtkSTLReader()
    self._orientationActor = vtkActor()
    self._orientationMapper = vtkDataSetMapper()
    self._orientationActor.SetMapper(self._orientationMapper)
    self._orientationActor.GetProperty().SetColor(colors.GetColor3d("Silver"))
    self._orientationMapper.SetInputConnection(self._stlReader.GetOutputPort())
    self._orientationWidget = vtkOrientationMarkerWidget()
    self._orientationWidget.SetViewport(0.75,0.75,1.0,1.0)
    self._orientationWidget.SetCurrentRenderer(self._renderer)
    self._orientationWidget.SetInteractor(self._renderWindow.GetInteractor())
    self._orientationWidget.SetOrientationMarker(self._orientationActor)
    self._orientationWidget.EnabledOn()  # <== application freeze-crash
    self._orientationWidget.InteractiveOff()
    stlPath = 'GUI' + os.path.sep + 'res' + os.path.sep + 'viewer' + os.path.sep
    self._stlReader.SetFileName(stlPath + "human_standing.stl")
    self._stlReader.Update()

    self.setView('axial')

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

    try:
      self._mainImageController.nameChangedSignal.disconnect(self.updateNameText)
    except:
      pass
    try:
      self._mainImageController.wwlChangedSignal.disconnect(self._setWWL)
    except:
      pass
    try:
      self._mainImageController.selectedPositionChangedSignal.disconnect(self._setPosition)
    except:
      pass

  def _lineWidgetInteraction(self, obj, event):
    if not self._lineWidgetNoInteractionYet:
      point1 = self._lineWidget.GetLineRepresentation().GetPoint1WorldPosition()
      point2 = self._lineWidget.GetLineRepresentation().GetPoint2WorldPosition()

      matrix = self._reslice.GetResliceAxes()
      point1 = matrix.MultiplyPoint((point1[0], point1[1], 0, 1))
      point2 = matrix.MultiplyPoint((point2[0], point2[1], 0, 1))

      num = 1000
      points0 = np.linspace(point1[0], point2[0], num)
      points1 = np.linspace(point1[1], point2[1], num)
      points2 = np.linspace(point1[2], point2[2], num)
      data = np.array(points1)

      imageData = self._reslice.GetInput(0)
      for i, p0 in enumerate(points0):
        ind = [0, 0, 0]
        imageData.TransformPhysicalPointToContinuousIndex((p0, points1[i], points2[i]), ind)
        data[i] = imageData.GetScalarComponentAsFloat(int(ind[0]), int(ind[1]), int(ind[2]), 0)

      x = np.linspace(0, sqrt((point2[0]-point1[0])*(point2[0]-point1[0]) + (point2[1]-point1[1])*(point2[1]-point1[1]) + (point2[2]-point1[2])*(point2[2]-point1[2])), num)
      self._lineWidgetCallback(x, data)

    self._lineWidgetNoInteractionYet = False

  def onLeftButtonPressed(self, obj=None, event='Press'):
    if 'Press' in event:
      self._leftButtonPress = True

      if self._lineWidgetEnabled:
        self._iStyle.OnLeftButtonDown()
        return

      if self._crossHairEnabled:
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

    if self._lineWidgetNoInteractionYet and self._lineWidgetEnabled:
      self._lineWidget.GetLineRepresentation().SetPoint1WorldPosition((worldPos[0], worldPos[1], 0.01))
      self._lineWidget.GetLineRepresentation().SetPoint2WorldPosition((worldPos[0], worldPos[1], 0.01))
      return

    if self._leftButtonPress and self._crossHairEnabled:
      self._mainImageController.setSelectedPosition((point[0], point[1], point[2]))

    if self._leftButtonPress and self._wwlEnabled:
      self._iStyle.OnMouseMove()
      self.__sendingWWL = True
      imageProperty = self._iStyle.GetCurrentImageProperty()
      self._mainImageController.setWWLValue((imageProperty.GetColorWindow(), imageProperty.GetColorLevel()))
      self.__sendingWWL = False

    if not self._leftButtonPress:
      self._iStyle.OnMouseMove()

  def onRightButtonPress(self, obj, event):
    if 'Press' in event:
      self._rightButtonPress = True
      self._iStyle.OnRightButtonDown()
    else:
      self._rightButtonPress = False
      self._iStyle.OnRightButtonUp()

  def onScroll(self, obj=None, event='Forward'):
    sliceSpacing = self._reslice.GetOutput().GetSpacing()[2]

    if 'Forward' in event:
      deltaY = sliceSpacing
    if 'Backward' in event:
      deltaY = -sliceSpacing

    self._reslice.Update()
    if self._crossHairEnabled:
      worldPos = self._mainImageController.getSelectedPosition()
      if worldPos is None:
        return

      matrix = self._reslice.GetResliceAxes()
      tform = vtkCommonMath.vtkMatrix4x4()
      tform.DeepCopy(matrix)
      tform.Invert()
      point = tform.MultiplyPoint((worldPos[0], worldPos[1], worldPos[2], 1))

    # Update reslice matrix
    matrix = self._reslice.GetResliceAxes()
    # move the center point that we are slicing through
    center = matrix.MultiplyPoint((0, 0, deltaY, 1))
    matrix.SetElement(0, 3, center[0])
    matrix.SetElement(1, 3, center[1])
    matrix.SetElement(2, 3, center[2])

    self._setResliceMatrix(matrix)

    if self._crossHairEnabled:
      point = matrix.MultiplyPoint((point[0], point[1], point[2] , 1))
      self._mainImageController.setSelectedPosition(point)

    if self._lineWidgetEnabled:
      self._lineWidgetInteraction(None, None)

  def renderOverlay(self):
    self._textActor.SetInput(self._mainText[0] + '\n' + self._mainText[1] + '\n' + self._mainText[2])
    self._renderWindow.Render()

  def setCrossHairEnabled(self, enabled):
    if enabled==self._crossHairEnabled:
      return

    self._crossHairEnabled = enabled
    if self._crossHairEnabled:
      self.setWWLEnabled(False)
      self._crossHairActor.VisibilityOn()
    else:
      self._crossHairActor.VisibilityOff()
      self._renderWindow.Render()
    self.crossHairEnabledSignal.emit(self._crossHairEnabled)

  def setLineWidgetEnabled(self, enabled):
    # enabled is either a callback method or False
    if not (enabled==False):
      self._lineWidgetCallback = enabled
      self._lineWidget.AddObserver("InteractionEvent", self._lineWidgetInteraction)
      self._lineWidget.AddObserver("EndInteractionEvent", self._lineWidgetInteraction)
      self._lineWidget.SetInteractor(self._renderWindow.GetInteractor())
      self._lineWidget.On()
      self._lineWidget.GetLineRepresentation().SetLineColor(1, 0, 0)
      self._lineWidgetNoInteractionYet = True
      self._lineWidgetEnabled = True
    else:
      self._lineWidgetCallback = None
      self._lineWidget.Off()
      self._lineWidgetEnabled = False
      self._renderWindow.Render()

    self.lineWidgeEnabledSignal.emit(self._lineWidgetEnabled)

  def setMainImage(self, imageController):
    if imageController is None:
      self._disconnectAll()

      self._reslice.RemoveAllInputs()
      self._mainImageController = None

      self._mainLayout.removeWidget(self._vtkWidget)
      self._vtkWidget.hide()
      self._mainLayout.addWidget(self._blackWidget)
      self._blackWidget.show()
      return

    if imageController == self._mainImageController:
      return

    self._disconnectAll()

    self._mainLayout.removeWidget(self._blackWidget)
    self._blackWidget.hide()
    self._mainLayout.addWidget(self._vtkWidget)
    self._vtkWidget.show()

    self._mainImageController = Image3DViewerController(imageController)

    image = self._mainImageController.data

    shape = image.getGridSize()
    imageData = image.data
    imageOrigin = image.origin
    imageSpacing = image.spacing
    imageData = np.swapaxes(imageData, 0, 2)
    num_array = np.array(np.ravel(imageData), dtype=np.float32)

    self._dataImporter.SetNumberOfScalarComponents(1)
    self._dataImporter.SetDataExtent(0, shape[0] - 1, 0, shape[1] - 1, 0, shape[2] - 1)
    self._dataImporter.SetWholeExtent(0, shape[0] - 1, 0, shape[1] - 1, 0, shape[2] - 1)
    self._dataImporter.SetDataSpacing(imageSpacing[0], imageSpacing[1], imageSpacing[2])
    self._dataImporter.SetDataOrigin(imageOrigin[0], imageOrigin[1], imageOrigin[2])
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

    if self._wwlEnabled:
      self._iStyle.StartWindowLevel()
      self._iStyle.OnLeftButtonUp()

    self._iStyle.SetCurrentImageNumber(0)

    self._setWWL(self._mainImageController.getWWLValue())
    self._setPosition(self._mainImageController.getSelectedPosition())

    self._renderer.ResetCamera()

    self._connectAll()

    self.updateNameText()

  def _setPosition(self, position):
    if self._mainImageController is None:
      return

    transfo_mat = vtkCommonMath.vtkMatrix4x4()
    transfo_mat.DeepCopy(self._viewMatrix)
    transfo_mat.Invert()
    posAfterInverse = transfo_mat.MultiplyPoint((position[0], position[1], position[2], 1))
    pos = self._viewMatrix.MultiplyPoint((0, 0, posAfterInverse[2], 1))

    self._reslice.Update()
    matrix = self._reslice.GetResliceAxes()
    matrix.SetElement(0, 3, pos[0])
    matrix.SetElement(1, 3, pos[1])
    matrix.SetElement(2, 3, pos[2])

    self._updateCurrentPositionText(position)

    if self._crossHairEnabled:
      points = vtkPoints()
      points.InsertNextPoint((posAfterInverse[0]-10, posAfterInverse[1], 0.01))
      points.InsertNextPoint((posAfterInverse[0]+10, posAfterInverse[1], 0.01))
      points.InsertNextPoint((posAfterInverse[0], posAfterInverse[1]-10, 0.01))
      points.InsertNextPoint((posAfterInverse[0], posAfterInverse[1]+10, 0.01))

      polyLine = vtkPolyLine()
      polyLine.GetPointIds().SetNumberOfIds(2)
      polyLine2 = vtkPolyLine()
      polyLine2.GetPointIds().SetNumberOfIds(2)
      for i in range(0, 2):
        polyLine.GetPointIds().SetId(i, i)
        polyLine2.GetPointIds().SetId(i, i+2)

      cells = vtkCellArray()
      cells.InsertNextCell(polyLine)
      cells.InsertNextCell(polyLine2)

      polyData = vtkPolyData()
      polyData.SetPoints(points)
      polyData.SetLines(cells)

      self._crossHairMapper.SetInputData(polyData)

    self._renderWindow.Render()

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

    if viewName == 'sagittal':
      resliceAxes = sagittal
      self._viewMatrix.DeepCopy(sagittal)
    if viewName == 'axial':
      resliceAxes = axial
      self._viewMatrix.DeepCopy(axial)
    if viewName == 'coronal':
      resliceAxes = coronal
      self._viewMatrix.DeepCopy(coronal)

    self._reslice.SetResliceAxes(resliceAxes)
    self._orientationActor.PokeMatrix(resliceAxes)

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

  def setWWLEnabled(self, enabled):
    if enabled==self._wwlEnabled:
      return

    self._wwlEnabled = enabled

    if self._wwlEnabled:
      self.setCrossHairEnabled(False)
    self.wwlEnabledSignal.emit(enabled)

  def _updateCurrentPositionText(self, position):
    try:
      imageData = self._reslice.GetInput(0)
      ind = [0, 0, 0]
      imageData.TransformPhysicalPointToContinuousIndex(position[0:3], ind)
      data = imageData.GetScalarComponentAsFloat(round(ind[0]), round(ind[1]), round(ind[2]), 0)
      self._mainText[0] = 'Value: ' + "{:.2f}".format(data)

      self._mainText[1] = 'Pos: ' + "{:.2f}".format(position[0]) + ' ' + "{:.2f}".format(position[1]) + ' ' + "{:.2f}".format(position[2])
    except:
      self._mainText[0] = ''
      self._mainText[1] = ''

    self.renderOverlay()

  def updateNameText(self):
    self._mainText[2] = self._mainImageController.getName()
    self.renderOverlay()
