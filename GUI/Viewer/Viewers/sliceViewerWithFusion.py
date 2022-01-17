import numpy as np
from vtkmodules import vtkImagingCore, vtkRenderingCore
from vtkmodules.vtkIOImage import vtkImageImport
from vtkmodules.vtkInteractionWidgets import vtkScalarBarWidget
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkRenderingCore import vtkTextActor

from GUI.Viewer.ViewerData.viewerImage3D import ViewerImage3D
from GUI.Viewer.Viewers.lookupTables import LookupTables
from GUI.Viewer.Viewers.sliceViewer import SliceViewerVTK


class SliceViewerWithFusion(SliceViewerVTK):
    def __init__(self, viewController):
        SliceViewerVTK.__init__(self, viewController)

        self._viewController = viewController
        self._secondaryImage = None
        self._secondaryActor = vtkRenderingCore.vtkImageActor()
        self._secondaryColor = vtkImagingCore.vtkImageMapToColors()
        self._secondaryMapper = self._secondaryActor.GetMapper()
        self._secondaryReslice = vtkImagingCore.vtkImageReslice()
        self._secondaryText = ['', '', '', '']
        self._colorbarActor = vtkScalarBarActor()
        self._dataImporter = vtkImageImport()


        self._secondaryTextActor = vtkTextActor()
        self._secondaryTextActor.GetTextProperty().SetFontSize(14)
        self._secondaryTextActor.GetTextProperty().SetColor(1, 0.5, 0)
        self._secondaryTextActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
        self._secondaryTextActor.SetPosition(0.5, 0.05)
        self._secondaryTextActor.GetTextProperty().SetJustificationToRight()
        self._secondaryTextActor.GetTextProperty().SetVerticalJustificationToBottom()
        self._renderer.AddActor(self._secondaryTextActor)

        self._colorbarActor.SetNumberOfLabels(5)
        self._colorbarActor.SetOrientationToVertical()
        self._colorbarActor.SetVisibility(False)
        self._colorbarActor.SetUnconstrainedFontSize(14)
        self._colorbarActor.SetMaximumWidthInPixels(20)


        self._colorbarWidget = vtkScalarBarWidget()


    @property
    def secondaryImage(self):
        if self._secondaryImage is None:
            return None

        return self._secondaryImage.data

    @secondaryImage.setter
    def secondaryImage(self, image):
        self._disconnectAllSecondary()

        if self.mainImage is None:
            return

        if image is None:
            self._secondaryReslice.RemoveAllInputs()
            self.showColorbar(False)
            self._secondaryImage = None
            return

        self._secondaryImage = ViewerImage3D(image)

        shape = image.gridSize
        imageData = image.imageArray
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

        self._secondaryReslice.SetOutputDimensionality(2)
        self._secondaryReslice.SetInterpolationModeToNearestNeighbor()

        # Map the image through the lookup table
        self.setLookuptable(LookupTables.getFusion(0.5))
        #TODO de-hardcode fusion range
        self.setFusionRange((-1024, 2000))

        self._secondaryReslice.SetResliceAxes(self._reslice.GetResliceAxes())

        self._renderer.AddActor(self._secondaryActor)

        self._secondaryReslice.SetInputConnection(self._dataImporter.GetOutputPort())
        self._secondaryColor.SetInputConnection(self._secondaryReslice.GetOutputPort())
        self._secondaryMapper.SetInputConnection(self._secondaryColor.GetOutputPort())

        self._colorbarWidget.SetInteractor(self._renderWindow.GetInteractor())
        self._colorbarWidget.SetScalarBarActor(self._colorbarActor)

        #self.showColorbar(self._viewController.getColorbarVisibility())
        self._renderWindow.GetInteractor().Start()

        self.updateSecondaryName(self._secondaryImage.name)

        self._connectAllSecondary()

        self._renderWindow.Render()


    def _connectAllSecondary(self):
        self._secondaryImage.nameChangedSignal.connect(self.updateSecondaryName)

    def _disconnectAllSecondary(self):
        if self._secondaryImage is None:
            return

        self._secondaryImage.nameChangedSignal.disconnect(self.updateSecondaryName)

    def setLookuptable(self, lookuptable):
        self._secondaryColor.SetLookupTable(lookuptable)
        self._colorbarActor.SetLookupTable(lookuptable)

    def setFusionRange(self, range):
        self._secondaryColor.GetLookupTable().SetRange(range[0], range[1])  # image intensity range

    def setPosition(self, position):
        super().setPosition(position)

    def showColorbar(self, visible):
        if self._secondaryImage is None:
            return

        if visible:
            self._colorbarActor.SetVisibility(True)
            self._colorbarWidget.On()
        else:
            self._colorbarActor.SetVisibility(False)
            self._colorbarWidget.Off()

        self._renderWindow.Render()

    def _updateCurrentPositionText(self, position):
        try:
            imageData = self._secondaryReslice.GetInput(0)
            ind = [0, 0, 0]
            imageData.TransformPhysicalPointToContinuousIndex(position[0:3], ind)
            data = imageData.GetScalarComponentAsFloat(round(ind[0]), round(ind[1]), round(ind[2]), 0)
            self._secondaryText[0] = 'Value: ' + "{:.2f}".format(data)

            self._secondaryText[1] = 'Pos: ' + "{:.2f}".format(position[0]) + ' ' + "{:.2f}".format(
                position[1]) + ' ' + "{:.2f}".format(position[2])
        except:
            self._secondaryText[0] = ''
            self._secondaryText[1] = ''

        # Call super after so that super will render()
        super()._updateCurrentPositionText(position)

    def updateSecondaryName(self, name):
        self._secondaryText[2] = name
        self.renderOverlay()

    def renderOverlay(self):
        self._secondaryTextActor.SetInput(self._secondaryText[0] + '\n' + self._secondaryText[1] + '\n' + self._secondaryText[2])
        super().renderOverlay()

