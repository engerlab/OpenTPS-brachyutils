from typing import Optional, Sequence

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingCore as vtkRenderingCore
import vtkmodules.vtkCommonCore as vtkCommonCore
from vtkmodules import vtkImagingCore, vtkCommonMath
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper

import numpy as np

from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer


class PrimaryImageLayer:
    def __init__(self, renderer, renderWindow, iStyle):
        colors = vtkNamedColors()

        self._image = None
        self._iStyle = iStyle
        self._mainActor = vtkRenderingCore.vtkImageActor()
        self._mainMapper = self._mainActor.GetMapper()
        self._orientationActor = vtkActor()
        self._orientationMapper = vtkDataSetMapper()
        self._orientationWidget = vtkOrientationMarkerWidget()
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._reslice = vtkImagingCore.vtkImageReslice()
        self._stlReader = vtkSTLReader()
        self._viewMatrix = vtkCommonMath.vtkMatrix4x4()

        self._mainMapper.SetSliceAtFocalPoint(True)

        self._orientationActor.SetMapper(self._orientationMapper)
        self._orientationActor.GetProperty().SetColor(colors.GetColor3d("Silver"))
        self._orientationMapper.SetInputConnection(self._stlReader.GetOutputPort())
        self._orientationWidget.SetViewport(0.8, 0.0, 1.0, 0.2)
        self._orientationWidget.SetCurrentRenderer(self._renderer)
        self._orientationWidget.SetInteractor(self._renderWindow.GetInteractor())
        self._orientationWidget.SetOrientationMarker(self._orientationActor)

        self._renderer.AddActor(self._mainActor)

        self._reslice.SetOutputDimensionality(2)
        self._reslice.SetInterpolationModeToNearestNeighbor()

    @property
    def image(self) -> Optional[Image3DForViewer]:
        if self._image is None:
            return None

        return self._image

    @image.setter
    def image(self, image: Optional[Image3DForViewer]):
        if image is None:
            self._reslice.RemoveAllInputs()
            self._disconnectAll()
            self._image = None
            return

        if image == self._image:
            return

        self._disconnectAll()

        self._image = image

        self._reslice.SetInputConnection(self._image.vtkOutputPort)

        # Create a greyscale lookup table
        table = vtkCommonCore.vtkLookupTable()
        table.SetRange(-1024, 1500)  # image intensity range
        table.SetValueRange(0.0, 1.0)  # from black to white
        table.SetSaturationRange(0.0, 0.0)  # no color saturation
        table.SetRampToLinear()
        table.Build()

        # Map the image through the lookup table
        color = vtkImagingCore.vtkImageMapToColors()
        color.SetLookupTable(table)
        color.SetInputConnection(self._reslice.GetOutputPort())

        self._mainMapper.SetInputConnection(color.GetOutputPort())

        self._connectAll()

    @property
    def resliceAxes(self):
        return self._reslice.GetResliceAxes()

    @resliceAxes.setter
    def resliceAxes(self, resliceAxes):
        self._reslice.SetResliceAxes(resliceAxes)
        self._orientationActor.PokeMatrix(resliceAxes)

    def getDataAtPosition(self, position: Sequence):

        ## old version to get the value from the vtk image
        # imageData = self._reslice.GetInput(0)
        # ind = [0, 0, 0]
        # imageData.TransformPhysicalPointToContinuousIndex(position[0:3], ind)
        # dataVTK = imageData.GetScalarComponentAsFloat(round(ind[0]), round(ind[1]), round(ind[2]), 0)

        ## new version to get the value from the numpy image
        voxelIndex = self.getVoxelIndexFromPosition(position)
        dataNumpy = self._image.imageArray[voxelIndex[0], voxelIndex[1], voxelIndex[2]]

        return dataNumpy

    def getVoxelIndexFromPosition(self, position: Sequence):

        positionInMM = np.array(position)
        origin = np.array(self._image.origin) ## dataMultiton magic makes all this available here
        spacing = np.array(self._image.spacing)

        shiftedPosInMM = positionInMM - origin
        posInVoxels = np.round(np.divide(shiftedPosInMM, spacing)).astype(np.int)

        return posInVoxels

    def _connectAll(self):
        self._image.wwlChangedSignal.connect(self._setWWL)

    def _disconnectAll(self):
        if self._image is None:
            return

        self._image.wwlChangedSignal.disconnect(self._setWWL)

    def _setWWL(self, wwl: Sequence):
        imageProperty = self._iStyle.GetCurrentImageProperty()
        if not (imageProperty is None):
            imageProperty.SetColorWindow(wwl[0])
            imageProperty.SetColorLevel(wwl[1])

            self._renderWindow.Render()
