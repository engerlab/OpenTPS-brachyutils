from functools import partial
from typing import Sequence, Union, Optional

import vtkmodules.vtkRenderingCore as vtkRenderingCore

from opentps.core.data import ROIContour
from opentps.core.data.images import ROIMask, Image3D
from opentps.gui.viewer.dataForViewer.ROIContourForViewer import ROIContourForViewer
from opentps.gui.viewer.dataForViewer.ROIMaskForViewer import ROIMaskForViewer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.lookupTables import uniqueColorLTTo3DLT
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.secondaryImage3DLayer_3D import \
    SecondaryImage3DLayer_3D


class ContourLayer_3D:
    def __init__(self, renderer, renderWindow, iStyle):
        self._contours = [] # Acts as a cache
        self._referenceImage = None
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._iStyle = iStyle
        self._vtkContours = []
        self._partialHandlers = []

    def close(self):
        for vtkContour in self._vtkContours:
            vtkContour.close()

    @property
    def contours(self) -> Sequence[Union[ROIContourForViewer, ROIMaskForViewer]]:
        return [contour for contour in self._contours]

    def setNewContour(self, contour:Union[ROIContour, ROIMask]):
        if isinstance(contour, ROIContour):
            contour = ROIContourForViewer(contour)
        elif isinstance(contour, ROIMask):
            contour = ROIMaskForViewer(contour)
        else:
            raise ValueError(str(type(contour)) + ' is not a valid type for a contour.')

        if contour in self._contours:
            return

        if not contour.visible:
            return

        #contour.referenceImage = self.referenceImage

        self._contours.append(contour)

        vtkContourObj = MaskLayer_3D(self._renderer, self._renderWindow, self._iStyle)

        if isinstance(contour, ROIContourForViewer):
            vtkContourObj.image = contour.asROIMaskForViewer()
        else:
            vtkContourObj.image = contour

        self._vtkContours.append(vtkContourObj)

        partialHandler = partial(self._handleVisibilityChange, contour)
        self._partialHandlers.append(partialHandler)
        contour.visibleChangedSignal.connect(partialHandler)

        self._renderWindow.Render()

    def update(self):
        for vtkContour in self._vtkContours:
            vtkContour.update()

    def _handleVisibilityChange(self, contour:Union[ROIContourForViewer, ROIMaskForViewer], visible):
        if not contour.visible:
            self._removeContour(contour)

    def _removeContour(self, contour:Union[ROIContourForViewer, ROIMaskForViewer]):
        contourIndex = self._contours.index(contour)
        vtkContourObj = self._vtkContours[contourIndex]
        partialHandler = self._partialHandlers[contourIndex]

        vtkContourObj.close()

        self._contours.remove(contour)
        self._vtkContours.remove(vtkContourObj)
        self._partialHandlers.remove(partialHandler)

        contour.visibleChangedSignal.disconnect(partialHandler)

    @property
    def referenceImage(self) -> Optional[Image3D]:
        return self._referenceImage

    @referenceImage.setter
    def referenceImage(self, image: Image3D):
        self._referenceImage = image

        for contour in self._contours:
            contour.referenceImage = self._referenceImage


class MaskLayer_3D(SecondaryImage3DLayer_3D):
    def __init__(self, renderer, renderWindow, iStyle):
        super().__init__(renderer, renderWindow, iStyle)

        self._volumeProperty = vtkRenderingCore.vtkVolumeProperty()
        self._volumeProperty.SetInterpolationTypeToLinear()
        self._volumeProperty.ShadeOn()
        self._volumeProperty.SetAmbient(0.4)
        self._volumeProperty.SetDiffuse(0.6)
        self._volumeProperty.SetSpecular(0.2)

    def _updateLookupTable(self, lt):
        volumeColor, volumeScalarOpacity, volumeGradientOpacity = uniqueColorLTTo3DLT(lt)
        self._volumeProperty.SetColor(volumeColor)
        self._volumeProperty.SetScalarOpacity(volumeScalarOpacity)
        self._volumeProperty.SetGradientOpacity(volumeGradientOpacity)

        self._renderWindow.Render()
