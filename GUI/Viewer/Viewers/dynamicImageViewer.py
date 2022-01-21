
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
        super().__init__()
        # QWidget.__init__(self)

        self._viewController = viewController

        self.dynPrimaryImageList = []
        self.dynSecondaryImageList = []
        self.dynContourList = []

        self.curDynIndex = 0

    def updateAll(self):

        self.curDynIndex += 1
        self.primaryImage = self.dynPrimaryImageList[self.curDynIndex]




