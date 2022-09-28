from typing import Optional

import vtkmodules.vtkRenderingCore as vtkRenderingCore

from opentps.gui.viewer.dataForViewer.genericImageForViewer import GenericImageForViewer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.lookupTables import fusionLTTo3DLT
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.primaryImage3DLayer_3D import PrimaryImage3DLayer_3D


class SecondaryImage3DLayer_3D(PrimaryImage3DLayer_3D):
    def __init__(self, renderer, renderWindow, iStyle):
        super().__init__(renderer, renderWindow, iStyle)

        self._volumeProperty = vtkRenderingCore.vtkVolumeProperty()
        self._volumeProperty.SetInterpolationTypeToLinear()
        self._volumeProperty.ShadeOn()
        self._volumeProperty.SetAmbient(0.4)
        self._volumeProperty.SetDiffuse(0.6)
        self._volumeProperty.SetSpecular(0.2)


    def _setImage(self, image:Optional[GenericImageForViewer]):
        super()._setImage(image)

        if not (self._image is None):
            self._updateLookupTable(self._image.lookupTable)

    def _updateLookupTable(self, lt):
        volumeColor, volumeScalarOpacity, volumeGradientOpacity = fusionLTTo3DLT(lt)
        self._volumeProperty.SetColor(volumeColor)
        self._volumeProperty.SetScalarOpacity(volumeScalarOpacity)
        self._volumeProperty.SetGradientOpacity(volumeGradientOpacity)

        self._renderWindow.Render()
