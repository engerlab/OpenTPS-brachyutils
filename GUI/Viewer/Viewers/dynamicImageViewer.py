

from GUI.Viewer.Viewers.imageViewer import ImageViewer
from GUI.Viewer.DataForViewer.dyn3DSeqForViewer import Dyn3DSeqForViewer


class DynamicImageViewer(ImageViewer):
    def __init__(self, viewController):
        super().__init__()
        # QWidget.__init__(self)

        self._viewController = viewController
        self.dynPrimImgSeq = None
        self.vtkDynPrimImgSeq = None

        self.dynPrimaryImageList = []
        self.dynSecondaryImageList = []
        self.dynContourList = []

        self.curPrimImgDynIdx = 0

    def setDynamicPrimaryImg(self, dynSeq):
        self.dynPrimImgSeq = dynSeq
        self.vtkDynPrimImgSeq = Dyn3DSeqForViewer(self.dynPrimImgSeq)


    def updateAll(self):

        self.curDynIndex += 1
        self.primaryImage = self.dynPrimaryImageList[self.curDynIndex]


    def next_image(self):
        # self.timer.stop()
        self.currentImageIndex += 1
        if self.currentImageIndex == len(self.image3D_viewerList):
            self.currentImageIndex = 0
        self.timer.start(
            self.imageListTimings[self.currentImageIndex + 1] - self.imageListTimings[self.currentImageIndex])
        self.update_viewer()
        if self.target_voxel:
            self.showVoxelInfo()




