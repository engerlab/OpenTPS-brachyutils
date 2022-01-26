
from vtkmodules.vtkCommonCore import vtkCommand

from GUI.Viewer.Viewers.imageViewer import ImageViewer
from GUI.Viewer.DataForViewer.dyn3DSeqForViewer import Dyn3DSeqForViewer


class DynamicImageViewer(ImageViewer):
    def __init__(self, viewController):
        super().__init__(viewController)

        self._viewController = viewController

        self.dynPrimaryImgSeq = None
        self.dynPrimaryImgSeqForViewer = None

        self.dynSecondaryImgSeq = None
        self.dynSecondaryImgSeqForViewer = None

        self.dynContourImgSeq = None
        self.dynContourImgSeqForViewer = None

        self.curPrimaryImgIdx = 0
        self.curSecondaryImgIdx = 0
        self.curContourImgIdx = 0

        self.loopStepNumber = 0


    @property
    def primaryImage(self):
        if self._primaryImageLayer.image is None:
            return None
        return self.dynPrimaryImgSeqForViewer

    @primaryImage.setter
    def primaryImage(self, dyn3DImgSeq):

        if dyn3DImgSeq is None:
            self._primaryImageLayer.image = None

            self._mainLayout.removeWidget(self._vtkWidget)
            self._vtkWidget.hide()
            self._mainLayout.addWidget(self._blackWidget)
            self._blackWidget.show()
            return


        if dyn3DImgSeq != self.dynPrimaryImgSeq:
            self.dynPrimaryImgSeq = dyn3DImgSeq
            self.dynPrimaryImgSeqForViewer = Dyn3DSeqForViewer(self.dynPrimaryImgSeq)

        self._primaryImageLayer.image = self.dynPrimaryImgSeqForViewer.image3DForViewerList[self.curPrimaryImgIdx]
        self._contourLayer.referenceImage = self.primaryImage
        self._textLayer.setPrimaryTextLine(2, self.primaryImage.name)


        # TODO: disconnect signals
        self._primaryImageLayer.image.selectedPositionChangedSignal.connect(self._handlePosition)
        self._primaryImageLayer.image.nameChangedSignal.connect(
            lambda name: self._textLayer.setPrimaryTextLine(2, name))

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

        self._profileWidget.primaryReslice = self._primaryImageLayer._reslice  # TODO : access of protected property is wrong

        self._renderer.ResetCamera()

        self._renderWindow.Render()

    def nextImage(self, index):
        self.curPrimaryImgIdx = index
        self._primaryImageLayer.image = self.dynPrimaryImgSeqForViewer.image3DForViewerList[self.curPrimaryImgIdx]
        self._renderWindow.Render()