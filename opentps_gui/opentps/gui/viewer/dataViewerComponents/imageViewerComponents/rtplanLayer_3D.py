import os.path
from typing import Optional

from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter
from vtkmodules.vtkIOGeometry import vtkSTLReader

from opentps.core.data.plan import RTPlan, PlanIonBeam
from opentps.gui.viewer.dataForViewer.polyDataForViewer import PolyDataForViewer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.polyData3DLayer_3D import PolyData3DLayer_3D
import opentps.gui.res.icons as iconModule

class BeamLayer_3D:
    def __init__(self, renderer, renderWindow):
        self._renderer = renderer
        self._renderWindow = renderWindow

        self._nozzleLayer = PolyData3DLayer_3D(self._renderer, self._renderWindow)

        filePath = os.path.join(iconModule.__path__[0], 'iba_nozzle.stl')
        self._stlReader = vtkSTLReader()
        self._stlReader.SetFileName(filePath)
        self._tformFilter = vtkTransformPolyDataFilter()
        self._tformFilter.SetTransform(self._tform(0, 0))
        self._tformFilter.SetInputConnection(self._stlReader.GetOutputPort())
        self._image = PolyDataForViewer(self._tformFilter)

    def close(self):
        self._nozzleLayer.close()
        self._tformFilter.RemoveAllInputs()

    def update(self):
        self._nozzleLayer.update()

    def _tform(self, gantryAngle, couchAngle):
        #TODO couchAngle
        tform = vtkTransform()
        tform.RotateY(-90)
        #tform.RotateY(90)
        tform.RotateZ(180)
        #tform.RotateX(90 + gantryAngle)
        tform.RotateX(180-gantryAngle)
        tform.Translate(0, 0, 0)

        return tform

    def setBeam(self, beam:PlanIonBeam):
        self._tformFilter.SetTransform(self._tform(beam.gantryAngle, beam.couchAngle))
        self._nozzleLayer.image = self._image

class RTPlanLayer_3D:
    def __init__(self, renderer, renderWindow):
        self._renderer = renderer
        self._renderWindow = renderWindow

        self._beamLayers = []
        self._plan = None

    def close(self):
        for bLayer in self._beamLayers:
            bLayer.close()

        self._beamLayers = []

        self._renderWindow.Render()

    def update(self):
        for bl in self._beamLayers:
            bl.update()

    @property
    def plan(self) -> Optional[RTPlan]:
        return self._plan

    def setPlan(self, plan:RTPlan):
        #TODO connect to plan.dataChangedSignal
        if plan is None:
            self._plan = None
            self.close()
            return
        elif self._plan == plan:
            return

        self._plan = plan

        self.close()

        for beam in plan:
            bLayer = BeamLayer_3D(self._renderer, self._renderWindow)
            bLayer.setBeam(beam)
            self._beamLayers.append(bLayer)

        self._renderer.ResetCamera()
        self._renderWindow.Render()