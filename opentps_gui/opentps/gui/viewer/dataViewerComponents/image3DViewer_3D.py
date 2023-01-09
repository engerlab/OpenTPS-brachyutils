from typing import Optional, Union

from PyQt5.QtWidgets import *

import vtkmodules.vtkRenderingCore as vtkRenderingCore
from vtkmodules import vtkInteractionStyle
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from opentps.core.data import ROIContour
from opentps.core.data.images import ROIMask
from opentps.core.data.images._image3D import Image3D
from opentps.core.data.plan import RTPlan
from opentps.core import Event
from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer
from opentps.gui.viewer.dataForViewer.image3DForViewer import Image3DForViewer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.contourLayer_3D import ContourLayer_3D
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.primaryImage3DLayer_3D import PrimaryImage3DLayer_3D
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.rtplanLayer_3D import RTPlanLayer_3D
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.secondaryImage3DLayer_3D import SecondaryImage3DLayer_3D
from opentps.gui.viewer.dataViewerComponents.blackEmptyPlot import BlackEmptyPlot


class Image3DViewer_3D(QWidget):
    def __init__(self, viewController, parent=None):
        QWidget.__init__(self, parent=parent)

        self.primaryImageSignal = Event(object)
        self.secondaryImageSignal = Event(object)

        self._blackWidget = BlackEmptyPlot(self)
        self._renderer = vtkRenderingCore.vtkRenderer()
        self._viewController = viewController
        self._vtkWidget = QVTKRenderWindowInteractor(self)
        self._mainLayout = QVBoxLayout()
        self._renderWindow = self._vtkWidget.GetRenderWindow()

        self._iStyle = vtkInteractionStyle.vtkInteractorStyleTrackballCamera()

        self._primaryImageLayer = PrimaryImage3DLayer_3D(self._renderer, self._renderWindow, self._iStyle)
        self._secondaryImageLayer = SecondaryImage3DLayer_3D(self._renderer, self._renderWindow, self._iStyle)
        self._contourLayer = ContourLayer_3D(self._renderer, self._renderWindow, self._iStyle)
        self._rtPlanLayer = RTPlanLayer_3D(self._renderer, self._renderWindow)


        self.setLayout(self._mainLayout)
        self._vtkWidget.hide()
        self._mainLayout.addWidget(self._blackWidget)
        self._blackWidget.show()
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        self._renderer.SetBackground(0, 0, 0)
        self._renderer.GetActiveCamera().SetParallelProjection(True)

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
        self._rtPlanLayer.close()
        self._contourLayer.close()
        self._primaryImageLayer.close()
        self._secondaryImageLayer.close()

    def show(self):
        super(Image3DViewer_3D, self).show()
        self.update()
        self._primaryImageLayer.update()
        self._secondaryImageLayer.update()
        self._rtPlanLayer.update()
        self._contourLayer.update()

    def update(self):
        self._primaryImageLayer.update()
        self._secondaryImageLayer.update()
        self._rtPlanLayer.update()


    @property
    def primaryImage(self) -> Optional[Image3D]:
        if self._primaryImageLayer.image is None:
            return None
        return self._primaryImageLayer.image.data

    @primaryImage.setter
    def primaryImage(self, image: Image3D):
        self._setPrimaryImageForViewer(Image3DForViewer(image))
        if self.isVisible():
            self.update()

        self.primaryImageSignal.emit(self.primaryImage)

    def _resetPrimaryImageLayer(self):
        self._primaryImageLayer.image = None
        self._mainLayout.removeWidget(self._vtkWidget)
        self._vtkWidget.hide()
        self._mainLayout.addWidget(self._blackWidget)
        self._blackWidget.show()

    def _setPrimaryImageForViewer(self, image:GenericImageForViewer):
        self._primaryImageLayer.image = image

        self._blackWidget.hide()
        self._mainLayout.removeWidget(self._blackWidget)
        self._mainLayout.addWidget(self._vtkWidget)
        self._vtkWidget.show()

    @property
    def secondaryImage(self) -> Optional[Image3D]:
        if self._secondaryImageLayer.image is None:
            return None
        return self._secondaryImageLayer.image.data

    @secondaryImage.setter
    def secondaryImage(self, image: Image3D):
        if self.primaryImage is None:
            return

        if image is None:
            self._secondaryImageLayer.image = None
            if self.isVisible():
                self.update()

            self.secondaryImageSignal.emit(self.secondaryImage)
            return
        else:
            self._secondaryImageLayer.image = Image3DForViewer(image)

        if self.isVisible():
            self.update()

        self._renderWindow.Render()

        self.secondaryImageSignal.emit(self.secondaryImage)

    @property
    def rtPlan(self) -> RTPlan:
        raise NotImplementedError

    @rtPlan.setter
    def rtPlan(self, plan: RTPlan):
        self._rtPlanLayer.setPlan(plan)

        if self.isVisible():
            self.update()

    def setNewContour(self, contour:Union[ROIContour, ROIMask]):
        self._contourLayer.setNewContour(contour)

        if self.isVisible():
            self._contourLayer.update()
