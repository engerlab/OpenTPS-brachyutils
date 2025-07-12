import typing

from PyQt5.QtWidgets import *

import vtkmodules.vtkRenderingCore as vtkRenderingCore
import vtkmodules.vtkInteractionStyle as vtkInteractionStyle
from vtkmodules import vtkCommonMath
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkRenderingCore import vtkCoordinate

from opentps.core.data.images import Image2D
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core import Event
from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer
from opentps.gui.viewer.dataForViewer.image2DForViewer import Image2DForViewer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.rtPlanLayer import RTPlanLayer
from opentps.gui.viewer.dataViewerComponents.blackEmptyPlot import BlackEmptyPlot
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.contourLayer import ContourLayer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.crossHairLayer import CrossHairLayer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.primaryImage2DLayer import PrimaryImage2DLayer
from opentps.gui.viewer.dataViewerComponents.profileWidget import ProfileWidget
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.secondaryImage2DLayer import SecondaryImage2DLayer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.textLayer import TextLayer


class Image2DViewer(QWidget):
    # class ViewerTypes(Enum):
    #     AXIAL = 'axial'
    #     CORONAL = 'coronal'
    #     SAGITTAL = 'sagittal'
    #     DEFAULT = 'sagittal'
    #
    # _viewerTypesList = iter(list(ViewerTypes))


    def __init__(self, viewController):
        QWidget.__init__(self)

        self.crossHairEnabledSignal = Event(bool)
        self.profileWidgeEnabledSignal = Event(bool)
        self.wwlEnabledSignal = Event(bool)
        self.wwlEnabledSignal = Event(bool)
        self.viewTypeChangedSignal = Event(object)
        self.primaryImageSignal = Event(object)
        self.secondaryImageSignal = Event(object)

        self._blackWidget = BlackEmptyPlot(self)
        self._crossHairEnabled = False
        self._iStyle = vtkInteractionStyle.vtkInteractorStyleImage()
        self._leftButtonPress = False
        self._mainLayout = QVBoxLayout()
        self._profileWidgetNoInteractionYet = False # Used to know if initial position of profile widget must be set
        self._renderer = vtkRenderingCore.vtkRenderer()
        self.__sendingWWL = False
        self._viewController = viewController
        self._viewMatrix = vtkCommonMath.vtkMatrix4x4()
        # self._viewType = self.ViewerTypes.DEFAULT
        self._vtkWidget = QVTKRenderWindowInteractor(self)
        self._wwlEnabled = False

        self._renderWindow = self._vtkWidget.GetRenderWindow()

        self._crossHairLayer = CrossHairLayer(self._renderer, self._renderWindow)
        self._primaryImage2DLayer = PrimaryImage2DLayer(self._renderer, self._renderWindow, self._iStyle)
        self._secondaryImageLayer = SecondaryImage2DLayer(self._renderer, self._renderWindow, self._iStyle)
        self._profileWidget = ProfileWidget(self._renderer, self._renderWindow)
        self._textLayer = TextLayer(self._renderer, self._renderWindow)
        self._contourLayer = ContourLayer(self._renderer, self._renderWindow)
        self._rtPlanLayer = RTPlanLayer(self._renderer, self._renderWindow)

        self._profileWidget.primaryLayer = self._primaryImage2DLayer
        self._profileWidget.secondaryLayer = self._secondaryImageLayer
        self._profileWidget.contourLayer = self._contourLayer

        # self._setViewType(self._viewType)
        # self._contourLayer.resliceAxes = self._viewMatrix
        # self._rtPlanLayer.resliceAxes = self._viewMatrix

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

        self._closed = False

    def closeEvent(self, QCloseEvent):
        if self._closed:
            return

        self._closed = True
        self.reset()
        self._renderWindow.Finalize()
        self._vtkWidget.close()
        del self._renderWindow, self._vtkWidget
        super().closeEvent(QCloseEvent)

    def reset(self):
        if not (self._primaryImage2DLayer.image is None):
            self._primaryImage2DLayer.image.selectedPositionChangedSignal.disconnect(self._handlePosition)
            self._primaryImage2DLayer.image.nameChangedSignal.disconnect(self._setPrimaryName)

        if not (self._secondaryImageLayer.image is None):
            self._secondaryImageLayer.image.nameChangedSignal.disconnect(self._setSecondaryName)

        self._primaryImage2DLayer.close()
        self._secondaryImageLayer.close()
        self._textLayer.close()
        self._contourLayer.close()
        self._crossHairLayer.close()
        self._rtPlanLayer.close()

    @property
    def rtPlan(self) -> RTPlan:
        raise NotImplementedError

    @rtPlan.setter
    def rtPlan(self, plan:RTPlan):
        if not self.primaryImage is None:
            self._rtPlanLayer.setPlan(plan, self.primaryImage)

    @property
    def primaryImage(self) -> Image2D:
        if self._primaryImage2DLayer.image is None:
            return None
        return self._primaryImage2DLayer.image.data

    @primaryImage.setter
    def primaryImage(self, image: Image2D):
        imageAlreadyDisplayed = image == self._primaryImage2DLayer.image or (not (self._primaryImage2DLayer.image is None) and image == self._primaryImage2DLayer.image.data)
        if imageAlreadyDisplayed:
            return

        if image is None:
            self._resetPrimaryImageLayer()
        else:
            self._setPrimaryImageForViewer(Image2DForViewer(image))

        self.primaryImageSignal.emit(self.primaryImage)

    def _resetPrimaryImageLayer(self):
        self._primaryImage2DLayer.image = None
        self._mainLayout.removeWidget(self._vtkWidget)
        self._vtkWidget.hide()
        self._mainLayout.addWidget(self._blackWidget)
        self._blackWidget.show()

    def _setPrimaryImageForViewer(self, image:GenericImageForViewer):

        print('in image2DVIewer _setPrimaryImageForViewer', type(image))

        self._primaryImage2DLayer.image = image
        self._contourLayer.referenceImage = image
        self._textLayer.setPrimaryTextLine(2, image.name)

        self._handlePosition(self._primaryImage2DLayer.image.selectedPosition)

        if not (self._primaryImage2DLayer.image is None):
            self._primaryImage2DLayer.image.selectedPositionChangedSignal.disconnect(self._handlePosition)
            self._primaryImage2DLayer.image.nameChangedSignal.disconnect(self._setPrimaryName)

        self._primaryImage2DLayer.image.selectedPositionChangedSignal.connect(self._handlePosition)
        self._primaryImage2DLayer.image.nameChangedSignal.connect(self._setPrimaryName)

        # self._primaryImage2DLayer.resliceAxes = self._viewMatrix
        self._contourLayer.resliceAxes = self._viewMatrix
        self._rtPlanLayer.resliceAxes = self._viewMatrix

        self._blackWidget.hide()
        self._mainLayout.removeWidget(self._blackWidget)
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

        self._renderer.ResetCamera()

        self._renderWindow.Render()

    def _setPrimaryName(self, name):
        self._textLayer.setPrimaryTextLine(2, name)

    @property
    def profileWidgetEnabled(self) -> bool:
        return self._profileWidget.enabled

    @profileWidgetEnabled.setter
    def profileWidgetEnabled(self, enabled: bool):
        if enabled==self._profileWidget.enabled:
            return

        if enabled and not self._profileWidget.enabled:
            self._profileWidgetNoInteractionYet = True
            self._profileWidget.callback = self._viewController.profileWidgetCallback
        else:
            self._profileWidgetNoInteractionYet = False
        self._profileWidget.enabled = enabled

        self.profileWidgeEnabledSignal.emit(self.profileWidgetEnabled)

    def setProfileWidgetEnabled(self, enabled):
        self.profileWidgetEnabled = enabled

    @property
    def secondaryImage(self) -> typing.Optional[Image2D]:
        if self._secondaryImageLayer.image is None:
            return None
        return self._secondaryImageLayer.image.data

    @secondaryImage.setter
    def secondaryImage(self, image: Image2D):
        if self.primaryImage is None:
            return

        imageAlreadyDisplayed = image == self._secondaryImageLayer.image or (not (self._secondaryImageLayer.image is None) and image == self._secondaryImageLayer.image.data)
        if imageAlreadyDisplayed:
            return

        self._secondaryImageLayer.image = Image2DForViewer(image)

        if image is None:
            self._secondaryImageLayer.image = None
            self.secondaryImageSignal.emit(self.secondaryImage)
            return

        self._secondaryImageLayer.resliceAxes = self._viewMatrix

        self._textLayer.setSecondaryTextLine(2, self.secondaryImage.name)

        if not (self._secondaryImageLayer.image is None):
            self._secondaryImageLayer.image.nameChangedSignal.disconnect(self._setSecondaryName)

        self._secondaryImageLayer.image.nameChangedSignal.connect(self._setSecondaryName)

        self._renderWindow.Render()

        self.secondaryImageSignal.emit(self.secondaryImage)

    def _setSecondaryName(self, name):
        self._textLayer.setSecondaryTextLine(2, name)

    @property
    def secondaryImageLayer(self):
        return self._secondaryImageLayer


    @property
    def viewType(self):
        return self._viewType

    @viewType.setter
    def viewType(self, viewType):
        if self._viewType == viewType:
            return

        self._setViewType(viewType)

    def _setViewType(self, viewType):
        self._viewType = viewType
        coronal = vtkCommonMath.vtkMatrix4x4()
        coronal.DeepCopy((1, 0, 0, 0,
                          0, 0, 1, 0,
                          0, 1, 0, 0,
                          0, 0, 0, 1))

        sagittal = vtkCommonMath.vtkMatrix4x4()
        sagittal.DeepCopy((0, 0, -1, 0,
                          1, 0, 0, 0,
                          0, 1, 0, 0,
                          0, 0, 0, 1))

        axial = vtkCommonMath.vtkMatrix4x4()
        axial.DeepCopy((1, 0, 0, 0,
                        0, -1, 0, 0,
                        0, 0, -1, 0,
                        0, 0, 0, 1))

        if self._viewType == self.ViewerTypes.SAGITTAL:
            self._viewMatrix = sagittal
        if self._viewType == self.ViewerTypes.AXIAL:
            self._viewMatrix = axial
        if self._viewType == self.ViewerTypes.CORONAL:
            self._viewMatrix = coronal
        else:
            ValueError('Invalid viewType')

        if not self.primaryImage is None:
            self._primaryImage2DLayer.resliceAxes = self._viewMatrix
            self._contourLayer.resliceAxes = self._viewMatrix
            self._rtPlanLayer.resliceAxes = self._viewMatrix
        if not self.secondaryImage is None:
            self._secondaryImageLayer.resliceAxes = self._viewMatrix

        self._renderer.ResetCamera()
        self._renderWindow.Render()

        self.viewTypeChangedSignal.emit(self._viewType)

    @property
    def crossHairEnabled(self) -> bool:
        return self._crossHairEnabled

    @crossHairEnabled.setter
    def crossHairEnabled(self, enabled: bool):
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

    def setCrossHairEnabled(self, enabled: bool):
        self.crossHairEnabled = enabled

    @property
    def wwlEnabled(self) -> bool:
        return self._wwlEnabled

    @wwlEnabled.setter
    def wwlEnabled(self, enabled: bool):
        if enabled == self._wwlEnabled:
            return

        self._wwlEnabled = enabled

        if self._wwlEnabled:
            self.crossHairEnabled = False
        self.wwlEnabledSignal.emit(enabled)

    def setWWLEnabled(self, enabled: bool):
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
            self._primaryImage2DLayer.image.selectedPosition = (point[0], point[1], point[2])

        if self._leftButtonPress and self._wwlEnabled:
            self._iStyle.OnMouseMove()
            self.__sendingWWL = True
            imageProperty = self._iStyle.GetCurrentImageProperty()
            self._primaryImage2DLayer.image.wwlValue = (imageProperty.GetColorWindow(), imageProperty.GetColorLevel())
            self.__sendingWWL = False

        if not self._leftButtonPress:
            self._iStyle.OnMouseMove()

    def onScroll(self, obj=None, event='Forward'):
        print(NotImplementedError)

    def _handlePosition(self, position: typing.Sequence):
        if not self._crossHairEnabled or position is None:
            self._textLayer.setPrimaryTextLine(0, '')
            self._textLayer.setPrimaryTextLine(1, '')

            if not self.secondaryImage is None:
                self._textLayer.setSecondaryTextLine(0, '')
                self._textLayer.setSecondaryTextLine(1, '')
            return

        transfo_mat = vtkCommonMath.vtkMatrix4x4()
        transfo_mat.DeepCopy(self._viewMatrix)
        transfo_mat.Invert()
        posAfterInverse = transfo_mat.MultiplyPoint((position[0], position[1], position[2], 1))

        pos = self._viewMatrix.MultiplyPoint((0, 0, posAfterInverse[2], 1))

        self._viewMatrix.SetElement(0, 3, pos[0])
        self._viewMatrix.SetElement(1, 3, pos[1])
        self._viewMatrix.SetElement(2, 3, pos[2])
        if self._crossHairEnabled:
            self._crossHairLayer.position = (posAfterInverse[0], posAfterInverse[1])

        try:
            data = self._primaryImage2DLayer.image.getDataAtPosition(position)

            self._textLayer.setPrimaryTextLine(0, 'Value: ' + "{:.2f}".format(data))
            # self._textLayer.setPrimaryTextLine(0, 'ValueNumpy: ' + "{:.2f}".format(dataNumpy))
            self._textLayer.setPrimaryTextLine(1,  'Pos: ' + "{:.2f}".format(position[0]) + ' ' + "{:.2f}".format(
                position[1]) + ' ' + "{:.2f}".format(position[2]))
        except:
            self._textLayer.setPrimaryTextLine(0, '')
            self._textLayer.setPrimaryTextLine(1, '')

        if not self.secondaryImage is None:
            try:
                data = self._secondaryImageLayer.image.getDataAtPosition(position)

                self._textLayer.setSecondaryTextLine(0, 'Value: ' + "{:.2f}".format(data))
                self._textLayer.setSecondaryTextLine(1, 'Pos: ' + "{:.2f}".format(position[0]) + ' ' + "{:.2f}".format(
                    position[1]) + ' ' + "{:.2f}".format(position[2]))
            except:
                self._textLayer.setSecondaryTextLine(0, '')
                self._textLayer.setSecondaryTextLine(1, '')
