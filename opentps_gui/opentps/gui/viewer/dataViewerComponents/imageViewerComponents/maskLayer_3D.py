
import vtkmodules.vtkRenderingCore as vtkRenderingCore

from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.primaryImage3DLayer_3D import PrimaryImage3DLayer_3D


class MaskLayer_3D(PrimaryImage3DLayer_3D):
    def __init__(self, renderer, renderWindow, iStyle):
        super().__init__(renderer, renderWindow, iStyle)

        self._volumeProperty = vtkRenderingCore.vtkVolumeProperty()
        self._volumeProperty.SetInterpolationTypeToLinear()
        self._volumeProperty.ShadeOn()
        self._volumeProperty.SetAmbient(0.4)
        self._volumeProperty.SetDiffuse(0.6)
        self._volumeProperty.SetSpecular(0.2)
