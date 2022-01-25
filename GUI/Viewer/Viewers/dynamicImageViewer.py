
from GUI.Viewer.Viewers.imageViewer import ImageViewer
from GUI.Viewer.DataForViewer.dyn3DSeqForViewer import Dyn3DSeqForViewer


class DynamicImageViewer(ImageViewer):
    def __init__(self, viewController):
        super().__init__(viewController)


        print('in init DynamicImageViewer')
        self._viewController = viewController

        self.dynPrimaryImgSeq = None
        self.vtkDynPrimaryImgSeq = None

        self.dynSecondaryImgSeq = None
        self.vtkDynSecondaryImgSeq = None

        self.dynContourImgSeq = None
        self.vtkDynContourImgSeq = None

        self.curPrimImgDynIdx = 0


    def setDynamicPrimaryImg(self, dynSeq):
        self.dynPrimaryImgSeq = dynSeq
        self.vtkDynPrimaryImgSeq = Dyn3DSeqForViewer(self.dynPrimaryImgSeq)


    def updateAll(self):
        self.curDynIndex += 1
        self.primaryImage = self.vtkDynPrimaryImgSeq[self.curDynIndex]


