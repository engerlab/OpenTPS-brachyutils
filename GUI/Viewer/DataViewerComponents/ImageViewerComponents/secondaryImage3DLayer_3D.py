from typing import Optional

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingCore as vtkRenderingCore

from GUI.Viewer.DataForViewer.genericImageForViewer import GenericImageForViewer
from GUI.Viewer.DataViewerComponents.ImageViewerComponents.lookupTables import fusionLTTo3DLT
from GUI.Viewer.DataViewerComponents.ImageViewerComponents.primaryImage3DLayer_3D import PrimaryImage3DLayer_3D


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
