import numpy as np
from vtkmodules.vtkImagingGeneral import vtkSimpleImageFilterExample

from opentps.core import Event
from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer
from opentps.gui.viewer.dataForViewer.image3DForViewer import Image3DForViewer


class Dyn3DSeqForViewer(GenericImageForViewer):
    def __init__(self, dyn3DSeq):
        super().__init__(dyn3DSeq)

        if hasattr(self, '_image3DForViewerList'):
            return

        self.dataChangedSignal = Event() # Not implemented in data class but required by opentps_core

        dyn3DSeq = self.data
        self._selectedPosition = np.array(dyn3DSeq.dyn3DImageList[0].origin) + np.array(dyn3DSeq.dyn3DImageList[0].gridSize) * np.array(dyn3DSeq.dyn3DImageList[0].spacing) / 2.0

        # This creates all image3DForViewers within the image sequence with the side effect that all VTK output port are initialized.
        self._image3DForViewerList = self._getImg3DForViewerList(dyn3DSeq.dyn3DImageList)

        self._simpleFilter = vtkSimpleImageFilterExample()
        self._currentIndexIn3DSeq = 0
        self._updateVTKOutputPort()
        self._vtkOutputPort = self._simpleFilter.GetOutputPort()
        self._range = (np.min(self.data.dyn3DImageList[0].imageArray), np.max(self.data.dyn3DImageList[0].imageArray))

    def _getImg3DForViewerList(self, dyn3DSeqImgList):
        vtkImageList = []
        for image in dyn3DSeqImgList:
            vtkImageList.append(Image3DForViewer(image))

        return vtkImageList

    @property
    def currentIndexIn3DSeq(self):
        return self._currentIndexIn3DSeq

    @currentIndexIn3DSeq.setter
    def currentIndexIn3DSeq(self, ind):
        if self._currentIndexIn3DSeq == ind:
            return

        self._currentIndexIn3DSeq = ind
        self._updateVTKOutputPort()

    def _updateVTKOutputPort(self):
        self._simpleFilter.RemoveAllInputs()
        currImageForViewer = self._image3DForViewerList[self._currentIndexIn3DSeq]
        self._simpleFilter.SetInputConnection(currImageForViewer.vtkOutputPort)

    @property
    def vtkOutputPort(self):
        return self._vtkOutputPort

