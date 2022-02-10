
from vtkmodules.vtkCommonCore import vtkCommand

from GUI.Viewer.DataViewerComponents.imageViewer import ImageViewer
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

            self._primaryImageLayer.image = self.dynPrimaryImgSeqForViewer

            self._inializeViewer()

    def nextImage(self, index):
        self.curPrimaryImgIdx = index
        self.dynPrimaryImgSeqForViewer.currentIndexIn3DSeq = index
        self._renderWindow.Render()

    @property
    def secondaryImage(self):
        return None

    def resetDynamicParameters(self):
        self.curPrimaryImgIdx = 0
        self.curSecondaryImgIdx = 0
        self.curContourImgIdx = 0

        self.loopStepNumber = 0