
__docformat__ = "restructuredtext en"
__all__ = ['CropWidget']

from typing import Optional, Sequence

import numpy as np
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QMainWindow, QVBoxLayout, QPushButton, QLabel, QFrame
from vtkmodules import vtkCommonMath
from vtkmodules.vtkInteractionWidgets import vtkBoxWidget2, vtkBoxRepresentation

from opentps.core.data.images._image3D import Image3D
from opentps.core.processing.imageProcessing.resampler3D import crop3DDataAroundBox
from opentps.gui.panels.patientDataPanel.patientDataSelection import PatientDataSelection
from opentps.gui.viewer.dataViewerComponents.image3DViewer import Image3DViewer
from opentps.gui.viewer.dataViewer import DroppedObject


class CropWidget(QMainWindow):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController

        self.setWindowTitle('Crop tool')
        self.resize(800, 600)

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self._mainLayout = QHBoxLayout()
        centralWidget.setLayout(self._mainLayout)

        self._viewers = ThreeViewsGrid(self._viewController)

        self._dragLabel = QLabel("Select as many images as you want to crop.\nDrop the image needed to create a box.", self)
        self._dragLabel.setWordWrap(True)

        self._cropDataButton = QPushButton('Crop all selected data')
        self._cropDataButton.clicked.connect(self._cropData)

        self._dataSelection = PatientDataSelection(self._viewController, self)

        self._menuFrame = QFrame(self)
        self._menuFrame.setFixedWidth(200)
        self._menuLayout = QVBoxLayout(self._menuFrame)
        self._menuFrame.setLayout(self._menuLayout)

        self._mainLayout.addWidget(self._menuFrame)
        self._menuLayout.addWidget(self._dragLabel)
        self._menuLayout.addWidget(self._dataSelection)
        self._menuLayout.addWidget(self._cropDataButton)
        self._mainLayout.addWidget(self._viewers)

    def closeEvent(self, event):
        self._viewers.close()
        super().closeEvent(event)

    def _cropData(self):
        selectedData = self._dataSelection.selectedData

        box = self._viewers.getBoundingBox()

        xx = np.array([box[0], box[1]])
        yy = np.array([box[2], box[3]])
        zz = np.array([box[4], box[5]])

        box = [[xx.min(), xx.max()], [yy.min(), yy.max()], [zz.min(), zz.max()]]

        for data in selectedData:
            crop3DDataAroundBox(data, box, marginInMM=[0, 0, 0])


class ThreeViewsGrid(QWidget):
    def __init__(self, viewController):
        super().__init__()

        self._viewController = viewController

        self._mainLayout = QHBoxLayout(self)
        self.setLayout(self._mainLayout)

        self._viewer0 = Image3DViewer(viewController)
        self._viewer1 = Image3DViewer(viewController)
        self._viewer2 = Image3DViewer(viewController)

        self._viewer0.viewType = Image3DViewer.ViewerTypes.CORONAL
        self._viewer1.viewType = Image3DViewer.ViewerTypes.AXIAL
        self._viewer2.viewType = Image3DViewer.ViewerTypes.SAGITTAL

        self._viewer0.crossHairEnabled = True
        self._viewer1.crossHairEnabled = True
        self._viewer2.crossHairEnabled = True

        self._mainLayout.addWidget(self._viewer0)
        self._mainLayout.addWidget(self._viewer1)
        self._mainLayout.addWidget(self._viewer2)

        self.setAcceptDrops(True)
        self.dragEnterEvent = lambda event: event.accept()
        self.dropEvent = lambda event: self._dropEvent(event)

    def close(self):
        self._viewer0.close()
        self._viewer1.close()
        self._viewer2.close()

    def _dropEvent(self, e):
        if e.mimeData().hasText():
            droppedIsImage = e.mimeData().text() == DroppedObject.DropTypes.IMAGE

            if droppedIsImage:
                e.accept()
                self._setMainImage(self._viewController.selectedImage)
                return
        e.ignore()


    def _setMainImage(self, image: Optional[Image3D]):
        if isinstance(image, Image3D) or (image is None):
            self._viewer0.primaryImage = image
            self._viewer1.primaryImage = image
            self._viewer2.primaryImage = image

            interactor0 = self._viewer0._renderWindow.GetInteractor()
            interactor1 = self._viewer1._renderWindow.GetInteractor()
            interactor2 = self._viewer2._renderWindow.GetInteractor()

            self.boxRep0 = vtkBoxRepresentation()
            self.boxRep0.SetPlaceFactor(1)
            self.boxRep0.PlaceWidget(self._viewer0._primaryImageLayer._mainActor.GetBounds())

            self.boxRep1 = vtkBoxRepresentation()
            self.boxRep1.SetPlaceFactor(1)
            self.boxRep1.PlaceWidget(self._viewer1._primaryImageLayer._mainActor.GetBounds())

            self.boxRep2 = vtkBoxRepresentation()
            self.boxRep2.SetPlaceFactor(1)
            self.boxRep2.PlaceWidget(self._viewer2._primaryImageLayer._mainActor.GetBounds())


            self.boxWidget0 = vtkBoxWidget2()
            self.boxWidget0.SetRotationEnabled(False)
            self.boxWidget0.SetInteractor(interactor0)
            self.boxWidget0.SetRepresentation(self.boxRep0)
            self.boxWidget0.On()

            self.boxWidget1 = vtkBoxWidget2()
            self.boxWidget1.SetRotationEnabled(False)
            self.boxWidget1.SetInteractor(interactor1)
            self.boxWidget1.SetRepresentation(self.boxRep1)
            self.boxWidget1.On()

            self.boxWidget2 = vtkBoxWidget2()
            self.boxWidget2.SetRotationEnabled(False)
            self.boxWidget2.SetInteractor(interactor2)
            self.boxWidget2.SetRepresentation(self.boxRep2)
            self.boxWidget2.On()

            self._viewer0._renderWindow.Render()
            self._viewer1._renderWindow.Render()
            self._viewer2._renderWindow.Render()

            interactor0.Start()
            interactor1.Start()
            interactor2.Start()

            self.boxWidget0.AddObserver('InteractionEvent', self.onInteraction0)
            self.boxWidget1.AddObserver('InteractionEvent', self.onInteraction1)
            self.boxWidget2.AddObserver('InteractionEvent', self.onInteraction2)

    def onInteraction0(self, obj, event):
        self.boxRep1.PlaceWidget(self._2DboundsFromViewerToViewer(self._viewer0, self.boxRep0, self._viewer1, self.boxRep1))
        self.boxRep2.PlaceWidget(self._2DboundsFromViewerToViewer(self._viewer0, self.boxRep0, self._viewer2, self.boxRep2))
        self._viewer1._renderWindow.Render()
        self._viewer2._renderWindow.Render()

    def onInteraction1(self, obj, event):
        self.boxRep0.PlaceWidget(self._2DboundsFromViewerToViewer(self._viewer1, self.boxRep1, self._viewer0, self.boxRep0))
        self.boxRep2.PlaceWidget(self._2DboundsFromViewerToViewer(self._viewer1, self.boxRep1, self._viewer2, self.boxRep2))
        self._viewer0._renderWindow.Render()
        self._viewer2._renderWindow.Render()

    def onInteraction2(self, obj, event):
        self.boxRep0.PlaceWidget(self._2DboundsFromViewerToViewer(self._viewer2, self.boxRep2, self._viewer0, self.boxRep0))
        self.boxRep1.PlaceWidget(self._2DboundsFromViewerToViewer(self._viewer2, self.boxRep2, self._viewer1, self.boxRep1))
        self._viewer0._renderWindow.Render()
        self._viewer1._renderWindow.Render()

    def _2DboundsFromViewerToViewer(self, viewer0:Image3DViewer, boxRep0, viewer1:Image3DViewer, boxRep1) -> Sequence[float]:
        bounds = self._boundsFromViewerToViewer(viewer0, boxRep0, viewer1, boxRep1)
        return [bounds[0], bounds[1], bounds[2], bounds[3], 0, 0]

    def _boundsFromViewerToViewer(self, viewer0:Image3DViewer, boxRep0, viewer1:Image3DViewer, boxRep1) -> Sequence[float]:
        bounds0 = boxRep0.GetBounds()
        bounds1 = boxRep1.GetBounds()

        corner0Odd = [bounds0[0], bounds0[2], bounds0[4]]
        corner0Even = [bounds0[1], bounds0[3], bounds0[5]]

        corner1Odd = [bounds1[0], bounds1[2], bounds1[4]]
        corner1Even = [bounds1[1], bounds1[3], bounds1[5]]


        tform0 = vtkCommonMath.vtkMatrix4x4()
        tform0.DeepCopy(viewer0._viewMatrix)

        tform0Inverted = vtkCommonMath.vtkMatrix4x4()
        tform0Inverted.DeepCopy(viewer0._viewMatrix)
        tform0Inverted.Invert()

        tform1 = vtkCommonMath.vtkMatrix4x4()
        tform1.DeepCopy(viewer1._viewMatrix)

        tform1Inverted = vtkCommonMath.vtkMatrix4x4()
        tform1Inverted.DeepCopy(viewer1._viewMatrix)
        tform1Inverted.Invert()

        corner1Odd_2 = tform1.MultiplyPoint((corner1Odd[0], corner1Odd[1], corner1Odd[2], 1))
        corner1Odd_2 = tform0Inverted.MultiplyPoint((corner1Odd_2[0], corner1Odd_2[1], corner1Odd_2[2], 1))

        corner0OddTransformed = tform0.MultiplyPoint((corner0Odd[0], corner0Odd[1], corner1Odd_2[2], 1))

        corner0Odd_2 = tform1Inverted.MultiplyPoint((corner0OddTransformed[0], corner0OddTransformed[1], corner0OddTransformed[2], 1))

        corner1Even_2 = tform1.MultiplyPoint((corner1Even[0], corner1Even[1], corner1Even[2], 1))
        corner1Even_2 = tform0Inverted.MultiplyPoint((corner1Even_2[0], corner1Even_2[1], corner1Even_2[2], 1))

        corner0EvenTransformed = tform0.MultiplyPoint((corner0Even[0], corner0Even[1], corner1Even_2[2], 1))

        corner0Even_2 = tform1Inverted.MultiplyPoint((corner0EvenTransformed[0], corner0EvenTransformed[1], corner0EvenTransformed[2], 1))

        return [corner0Odd_2[0], corner0Even_2[0], corner0Odd_2[1], corner0Even_2[1], corner0Odd_2[2], corner0Even_2[2]]


    def getBoundingBox(self):
        viewer0 = self._viewer0
        viewer1 = self._viewer1

        boxRep0 = self.boxRep0
        boxRep1 = self.boxRep1

        bounds0 = boxRep0.GetBounds()
        bounds1 = boxRep1.GetBounds()

        corner0Odd = [bounds0[0], bounds0[2], bounds0[4]]
        corner0Even = [bounds0[1], bounds0[3], bounds0[5]]

        corner1Odd = [bounds1[0], bounds1[2], bounds1[4]]
        corner1Even = [bounds1[1], bounds1[3], bounds1[5]]

        tform0 = vtkCommonMath.vtkMatrix4x4()
        tform0.DeepCopy(viewer0._viewMatrix)

        tform0Inverted = vtkCommonMath.vtkMatrix4x4()
        tform0Inverted.DeepCopy(viewer0._viewMatrix)
        tform0Inverted.Invert()

        tform1 = vtkCommonMath.vtkMatrix4x4()
        tform1.DeepCopy(viewer1._viewMatrix)

        tform1Inverted = vtkCommonMath.vtkMatrix4x4()
        tform1Inverted.DeepCopy(viewer1._viewMatrix)
        tform1Inverted.Invert()

        corner1Odd_2 = tform1.MultiplyPoint((corner1Odd[0], corner1Odd[1], corner1Odd[2], 1))
        corner1Odd_2 = tform0Inverted.MultiplyPoint((corner1Odd_2[0], corner1Odd_2[1], corner1Odd_2[2], 1))

        corner0OddTransformed = tform0.MultiplyPoint((corner0Odd[0], corner0Odd[1], corner1Odd_2[2], 1))


        corner1Even_2 = tform1.MultiplyPoint((corner1Even[0], corner1Even[1], corner1Even[2], 1))
        corner1Even_2 = tform0Inverted.MultiplyPoint((corner1Even_2[0], corner1Even_2[1], corner1Even_2[2], 1))

        corner0EvenTransformed = tform0.MultiplyPoint((corner0Even[0], corner0Even[1], corner1Even_2[2], 1))

        return [corner0OddTransformed[0], corner0EvenTransformed[0], corner0OddTransformed[1], corner0EvenTransformed[1], corner0OddTransformed[2], corner0EvenTransformed[2]]