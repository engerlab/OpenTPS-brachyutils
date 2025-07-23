import numpy as np
from vtkmodules.vtkImagingGeneral import vtkSimpleImageFilterExample

from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer
from opentps.gui.viewer.dataForViewer.image2DForViewer import Image2DForViewer


class Dyn2DSeqForViewer(GenericImageForViewer):
    def __init__(self, dyn2DSeq):
        super().__init__(dyn2DSeq)

        if hasattr(self, '_image3DForViewerList'):
            return

        dyn2DSeq = self.data
        self._selectedPosition = np.array(dyn2DSeq.dyn2DImageList[0].origin) + np.array(dyn2DSeq.dyn2DImageList[0].gridSize) * np.array(dyn2DSeq.dyn2DImageList[0].spacing) / 2.0

        # This creates all image3DForViewers within the image sequence with the side effect that all VTK output port are initialized.
        self._image2DForViewerList = self._getImg2DForViewerList(dyn2DSeq.dyn2DImageList)

        self._simpleFilter = vtkSimpleImageFilterExample()
        self._currentIndexIn2DSeq = 0
        self._updateVTKOutputPort()
        self._vtkOutputPort = self._simpleFilter.GetOutputPort()
        self._range = (np.min(self.data.dyn2DImageList[0].imageArray), np.max(self.data.dyn2DImageList[0].imageArray))

    def _getImg2DForViewerList(self, dyn2DSeqImgList):
        vtkImageList = []
        for image in dyn2DSeqImgList:
            vtkImageList.append(Image2DForViewer(image))

        return vtkImageList

    @property
    def currentIndexIn2DSeq(self):
        return self._currentIndexIn2DSeq

    @currentIndexIn2DSeq.setter
    def currentIndexIn2DSeq(self, ind):
        if self._currentIndexIn2DSeq == ind:
            return

        self._currentIndexIn2DSeq = ind
        self._updateVTKOutputPort()

    def _updateVTKOutputPort(self):
        self._simpleFilter.RemoveAllInputs()
        currImageForViewer = self._image2DForViewerList[self._currentIndexIn2DSeq]
        self._simpleFilter.SetInputConnection(currImageForViewer.vtkOutputPort)

    @property
    def vtkOutputPort(self):
        return self._vtkOutputPort

