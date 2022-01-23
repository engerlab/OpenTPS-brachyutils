
from PyQt5.QtWidgets import *


import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingCore as vtkRenderingCore
import vtkmodules.vtkInteractionStyle as vtkInteractionStyle
from vtkmodules import vtkCommonMath
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkRenderingCore import vtkCoordinate

from Core.event import Event
from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer
from GUI.Viewer.Viewers.blackEmptyPlot import BlackEmptyPlot
from GUI.Viewer.Viewers.contourLayer import ContourLayer
from GUI.Viewer.Viewers.crossHairLayer import CrossHairLayer
from GUI.Viewer.Viewers.primaryImageLayer import PrimaryImageLayer
from GUI.Viewer.Viewers.profileWidget import ProfileWidget
from GUI.Viewer.Viewers.secondaryImageLayer import SecondaryImageLayer
from GUI.Viewer.Viewers.textLayer import TextLayer


class ImageViewer(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self.crossHairEnabledSignal = Event(bool)
        self.profileWidgeEnabledSignal = Event(bool)
        self.wwlEnabledSignal = Event(bool)
        self.wwlEnabledSignal = Event(bool)

        self._blackWidget = BlackEmptyPlot()
        self._crossHairEnabled = False
        self._iStyle = vtkInteractionStyle.vtkInteractorStyleImage()
        self._leftButtonPress = False
        self._mainLayout = QVBoxLayout()
        self._profileWidgetNoInteractionYet = False # Used to know if initial position of profile widget must be set
        self._renderer = vtkRenderingCore.vtkRenderer()
        self.__sendingWWL = False
        self._viewController = viewController
        self._viewMatrix = vtkCommonMath.vtkMatrix4x4()
        self._viewType = 'axial'
        self._vtkWidget = QVTKRenderWindowInteractor(self)
        self._wwlEnabled = False

        self._renderWindow = self._vtkWidget.GetRenderWindow()

        self._crossHairLayer = CrossHairLayer(self._renderer, self._renderWindow)
        self._primaryImageLayer = PrimaryImageLayer(self._renderer, self._renderWindow, self._iStyle)
        self._profileWidget = ProfileWidget(self._renderer, self._renderWindow)
        self._secondaryImageLayer = SecondaryImageLayer(self._renderer, self._renderWindow, self._iStyle)
        self._textLayer = TextLayer(self._renderer, self._renderWindow)
        self._contourLayer = ContourLayer(self._renderer, self._renderWindow)

        self.viewType = self._viewType # Updates _viewMatrix
        self._contourLayer.resliceAxes = self._viewMatrix

        self.setLayout(self._mainLayout)
        self._vtkWidget.hide()
        self._mainLayout.addWidget(self._blackWidget)
        self._blackWidget.show()
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        self._renderer.SetBackground(0, 0, 0)
        self._renderer.GetActiveCamera().SetParallelProjection(True)

        self._iStyle.SetInteractionModeToImageSlicing()

        self._iStyle.AddObserver("MouseWheelForwardEvent", self.onScroll)
        self._iStyle.AddObserver("MouseWheelBackwardEvent", self.onScroll)
        self._iStyle.AddObserver("MouseMoveEvent", self.onMouseMove)
        self._iStyle.AddObserver("LeftButtonPressEvent", self.onLeftButtonPressed)
        self._iStyle.AddObserver("LeftButtonReleaseEvent", self.onLeftButtonPressed)

        self._renderWindow.GetInteractor().SetInteractorStyle(self._iStyle)
        self._renderWindow.AddRenderer(self._renderer)

        # TODO: Disconnect signals
        self._viewController.crossHairEnabledSignal.connect(self._setCrossHairEnabled)
        self._viewController.lineWidgetEnabledSignal.connect(self._setProfileWidgetEnabled)
        self._viewController.showContourSignal.connect(self._contourLayer.setNewContour)
        self._viewController.windowLevelEnabledSignal.connect(self._setWWLEnabled)



    @property
    def primaryImage(self):
        return self._primaryImageLayer.image

    @primaryImage.setter
    def primaryImage(self, image):
        if image is None:
            self._primaryImageLayer.image = None

            self._mainLayout.removeWidget(self._vtkWidget)
            self._vtkWidget.hide()
            self._mainLayout.addWidget(self._blackWidget)
            self._blackWidget.show()
            return

        self._primaryImageLayer.image = Image3DForViewer(image)
        self._contourLayer.referenceImage = self.primaryImage
        self._textLayer.setPrimaryTextLine(2, self.primaryImage.name)

        #TODO: disconnect signals
        self._primaryImageLayer.image.selectedPositionChangedSignal.connect(self._handlePosition)
        self._primaryImageLayer.image.nameChangedSignal.connect(lambda name: self._textLayer.setPrimaryTextLine(2, name))

        self._primaryImageLayer.resliceAxes = self._viewMatrix
        self._contourLayer.resliceAxes = self._viewMatrix

        self._mainLayout.removeWidget(self._blackWidget)
        self._blackWidget.hide()
        self._mainLayout.addWidget(self._vtkWidget)
        self._vtkWidget.show()

        # Start interaction
        self._renderWindow.GetInteractor().Start()

        # Trick to instantiate image property in iStyle
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

        self._profileWidget.primaryReslice = self._primaryImageLayer._reslice #TODO : access of protected property is wrong

        self._renderer.ResetCamera()

        self._renderWindow.Render()

    @property
    def profileWidgetEnabled(self):
        return self._profileWidget.enabled

    @profileWidgetEnabled.setter
    def profileWidgetEnabled(self, enabled):
        if enabled==self._profileWidget.enabled:
            return

        if enabled and not self._profileWidget.enabled:
            self._profileWidgetNoInteractionYet = True
            self._profileWidget.callback = self._viewController.lineWidgetCallback
        else:
            self._profileWidgetNoInteractionYet = False
        self._profileWidget.enabled = enabled

        self.profileWidgeEnabledSignal.emit(self.profileWidgetEnabled)

    def _setProfileWidgetEnabled(self, enabled):
        self.profileWidgetEnabled = enabled

    @property
    def secondaryImage(self):
        return self._secondaryImageLayer.image

    @secondaryImage.setter
    def secondaryImage(self, image):
        if self.primaryImage is None:
            return

        self._secondaryImageLayer.image = Image3DForViewer(image)

        self._secondaryImageLayer.resliceAxes = self._viewMatrix

        self._textLayer.setSecondaryTextLine(2, self.primaryImage.name)

        #TODO: disconnect signal
        self._primaryImageLayer.image.nameChangedSignal.connect(
            lambda name: self._textLayer.setSecondaryTextLine(2, name))

        self._renderWindow.Render()


    @property
    def viewType(self):
        return self._viewType

    @viewType.setter
    def viewType(self, viewType):
        self._viewType = viewType
        axial = vtkCommonMath.vtkMatrix4x4()
        axial.DeepCopy((1, 0, 0, 0,
                        0, 0, 1, 0,
                        0, 1, 0, 0,
                        0, 0, 0, 1))

        coronal = vtkCommonMath.vtkMatrix4x4()
        coronal.DeepCopy((0, 0, -1, 0,
                          1, 0, 0, 0,
                          0, 1, 0, 0,
                          0, 0, 0, 1))

        sagittal = vtkCommonMath.vtkMatrix4x4()
        sagittal.DeepCopy((1, 0, 0, 0,
                           0, -1, 0, 0,
                           0, 0, -1, 0,
                           0, 0, 0, 1))

        if self._viewType == 'sagittal':
            self._viewMatrix = sagittal
        if self._viewType == 'axial':
            self._viewMatrix = axial
        if self._viewType == 'coronal':
            self._viewMatrix = coronal

        if not self.primaryImage is None:
            self._primaryImageLayer.resliceAxes = self._viewMatrix
            self._contourLayer.resliceAxes = self._viewMatrix
            self._renderWindow.Render()
        if not self.secondaryImage is None:
            self._secondaryImageLayer.resliceAxes = self._viewMatrix
            self._renderWindow.Render()

    @property
    def crossHairEnabled(self):
        return self._crossHairEnabled

    @crossHairEnabled.setter
    def crossHairEnabled(self, enabled):
        if enabled == self._crossHairEnabled:
            return

        self._crossHairEnabled = enabled
        if self._crossHairEnabled:
            self.wwlEnabled = False
            self._crossHairLayer.visible = True
        else:
            self._crossHairLayer.visible = False
            self._handlePosition(None)
            self._renderWindow.Render()
        self.crossHairEnabledSignal.emit(self._crossHairEnabled)

    def _setCrossHairEnabled(self, enabled):
        self.crossHairEnabled = enabled

    @property
    def wwlEnabled(self):
        return self._wwlEnabled

    @wwlEnabled.setter
    def wwlEnabled(self, enabled):
        if enabled == self._wwlEnabled:
            return

        self._wwlEnabled = enabled

        if self._wwlEnabled:
            self.crossHairEnabled = False
        self.wwlEnabledSignal.emit(enabled)

    def _setWWLEnabled(self, enabled):
        self.wwlEnabled = enabled

    def onLeftButtonPressed(self, obj=None, event='Press'):
        if 'Press' in event:
            self._leftButtonPress = True

            if self.profileWidgetEnabled:
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

        point = self._viewMatrix.MultiplyPoint((worldPos[0], worldPos[1], 0, 1))

        if self.profileWidgetEnabled and self._profileWidgetNoInteractionYet and self._leftButtonPress:
            self._profileWidget.setInitialPosition((worldPos[0], worldPos[1]))
            self._profileWidgetNoInteractionYet = False
            return

        if self._crossHairEnabled and self._leftButtonPress:
            self.primaryImage.selectedPosition = (point[0], point[1], point[2])

        if self._leftButtonPress and self._wwlEnabled:
            self._iStyle.OnMouseMove()
            self.__sendingWWL = True
            imageProperty = self._iStyle.GetCurrentImageProperty()
            self.primaryImage.wwlValue = (imageProperty.GetColorWindow(), imageProperty.GetColorLevel())
            self.__sendingWWL = False

        if not self._leftButtonPress:
            self._iStyle.OnMouseMove()

    def onScroll(self, obj=None, event='Forward'):
        sliceSpacing = self._primaryImageLayer._reslice.GetOutput().GetSpacing()[2]

        deltaY = 0.
        if 'Forward' in event:
            deltaY = sliceSpacing
        if 'Backward' in event:
            deltaY = -sliceSpacing

        point = (0., 0., 0., 0.)
        if self._crossHairEnabled:
            worldPos = self.primaryImage.selectedPosition
            if worldPos is None:
                return

            tform = vtkCommonMath.vtkMatrix4x4()
            tform.DeepCopy(self._viewMatrix)
            tform.Invert()
            point = tform.MultiplyPoint((worldPos[0], worldPos[1], worldPos[2], 1))

        # move the center point that we are slicing through
        center = self._viewMatrix.MultiplyPoint((0, 0, deltaY, 1))
        self._viewMatrix.SetElement(0, 3, center[0])
        self._viewMatrix.SetElement(1, 3, center[1])
        self._viewMatrix.SetElement(2, 3, center[2])

        if self._crossHairEnabled:
            point = self._viewMatrix.MultiplyPoint((point[0], point[1], point[2], 1))
            self.primaryImage.selectedPosition = point

        if self.profileWidgetEnabled:
            self.onprofileWidgetInteraction(None, None)

        self._renderWindow.Render()

    def _handlePosition(self, position):
        if self._crossHairEnabled:
            transfo_mat = vtkCommonMath.vtkMatrix4x4()
            transfo_mat.DeepCopy(self._viewMatrix)
            transfo_mat.Invert()
            posAfterInverse = transfo_mat.MultiplyPoint((position[0], position[1], position[2], 1))

            self._crossHairLayer.position = (posAfterInverse[0], posAfterInverse[1])
        else:
            self._textLayer.setPrimaryTextLine(0, '')
            self._textLayer.setPrimaryTextLine(1, '')

            if not self.secondaryImage is None:
                self._textLayer.setSecondaryTextLine(0, '')
                self._textLayer.setSecondaryTextLine(1, '')

            return

        try:
            data = self._primaryImageLayer.getDataAtPosition(position)

            self._textLayer.setPrimaryTextLine(0, 'Value: ' + "{:.2f}".format(data))
            self._textLayer.setPrimaryTextLine(1,  'Pos: ' + "{:.2f}".format(position[0]) + ' ' + "{:.2f}".format(
                position[1]) + ' ' + "{:.2f}".format(position[2]))
        except:
            self._textLayer.setPrimaryTextLine(0, '')
            self._textLayer.setPrimaryTextLine(1, '')

        if not self.secondaryImage is None:
            try:
                data = self._secondaryImageLayer.getDataAtPosition(position)

                self._textLayer.setSecondaryTextLine(0, 'Value: ' + "{:.2f}".format(data))
                self._textLayer.setSecondaryTextLine(1, 'Pos: ' + "{:.2f}".format(position[0]) + ' ' + "{:.2f}".format(
                    position[1]) + ' ' + "{:.2f}".format(position[2]))
            except:
                self._textLayer.setSecondaryTextLine(0, '')
                self._textLayer.setSecondaryTextLine(1, '')
