
from PyQt5.QtWidgets import *

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingCore as vtkRenderingCore
import vtkmodules.vtkInteractionStyle as vtkInteractionStyle
from vtkmodules import vtkCommonMath
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkRenderingCore import vtkCoordinate

from Core.event import Event
from GUI.Viewer.ViewerData.viewerDynSeq import ViewerDynSeq
from GUI.Viewer.ViewerData.viewerImage3D import ViewerImage3D
from GUI.Viewer.Viewers.blackEmptyPlot import BlackEmptyPlot
from GUI.Viewer.Viewers.contourLayer import ContourLayer
from GUI.Viewer.Viewers.crossHairLayer import CrossHairLayer
from GUI.Viewer.Viewers.primaryImageLayer import PrimaryImageLayer
from GUI.Viewer.Viewers.profileWidget import ProfileWidget
from GUI.Viewer.Viewers.secondaryImageLayer import SecondaryImageLayer
from GUI.Viewer.Viewers.textLayer import TextLayer

from GUI.Viewer.Viewers.imageViewer import ImageViewer


class DynamicImageViewer(ImageViewer):
    def __init__(self, viewController):
        super().__init__(viewController)

        self._dynSeq = None

    @property
    def dynSeq(self):
        return self._dynSeq.data

    @dynSeq.setter
    def dynSeq(self, seq):
        self._dynSeq = ViewerDynSeq(seq)
        self.primaryImage = seq.dyn3DImageList[0]

        self._dynSeq.vtkOutputPortChangedSignal.connect(self._setVTKInput)

    def _setVTKInput(self, vtkOutputPort):
        self._primaryImageLayer._reslice.RemoveAllInputConnections(0)
        self._primaryImageLayer._reslice.SetInputConnection(vtkOutputPort)
        self._primaryImageLayer._reslice.Update()
        self._renderWindow.Render()
