from opentps.gui.viewer.dataViewerComponents.image2DViewer import Image2DViewer
from opentps.gui.viewer.dataForViewer.dyn2DSeqForViewer import Dyn2DSeqForViewer


class DynamicImage2DViewer(Image2DViewer):
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

        print('in dynamicImage2DVIewer, primaryImage (property)')
        if self._primaryImageLayer.image is None:
            return None
        return self.dynPrimaryImgSeqForViewer

    @primaryImage.setter
    def primaryImage(self, dyn3DImgSeq):
        if dyn3DImgSeq is None:
            self.dynPrimaryImgSeq = None
            self.dynPrimaryImgSeqForViewer = None
            super().image = None
        elif dyn3DImgSeq != self.dynPrimaryImgSeq:
            self.dynPrimaryImgSeq = dyn3DImgSeq
            self.dynPrimaryImgSeqForViewer = Dyn2DSeqForViewer(self.dynPrimaryImgSeq)
            super()._setPrimaryImageForViewer(self.dynPrimaryImgSeqForViewer)

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