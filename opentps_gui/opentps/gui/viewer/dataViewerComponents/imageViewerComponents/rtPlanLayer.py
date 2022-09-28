from typing import Optional

from vtkmodules import vtkCommonMath
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyLine, vtkCellArray, vtkPolyData
from vtkmodules.vtkFiltersSources import vtkSphereSource, vtkLineSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from opentps.core.data.images._image3D import Image3D
from opentps.core.data.plan import PlanIonBeam
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.processing.imageProcessing import imageTransform3D


class BeamLayer:
    def __init__(self, renderer, renderWindow):
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._resliceAxes = None

        self._sphereSource = vtkSphereSource()
        self._sphereSource.SetCenter(0.0, 0.0, 0.0)
        self._sphereSource.SetRadius(5.0)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(self._sphereSource.GetOutputPort())

        colors = vtkNamedColors()

        self._sphereActor = vtkActor()
        self._sphereActor.SetMapper(mapper)
        self._sphereActor.GetProperty().SetColor(colors.GetColor3d("Fuchsia"))
        self._sphereActor.SetVisibility(False)

        renderer.AddActor(self._sphereActor)

        p0 = [0.0, 0.0, 0.0]
        p1 = [0.0, 0.0, 0.0]

        self._lineSource = vtkLineSource()
        self._lineSource.SetPoint1(p0)
        self._lineSource.SetPoint2(p1)

        self._lineMapper = vtkPolyDataMapper()

        self._lineActor = vtkActor()
        self._lineActor.SetMapper(self._lineMapper)
        self._lineActor.GetProperty().SetColor(colors.GetColor3d("Fuchsia"))
        self._lineActor.SetVisibility(False)

        renderer.AddActor(self._lineActor)

    def close(self):
        self._sphereActor.SetVisibility(False)
        self._lineActor.SetVisibility(False)

        self._renderer.RemoveActor(self._sphereActor)
        self._renderer.RemoveActor(self._lineActor)

    @property
    def resliceAxes(self):
        return self._resliceAxes

    @resliceAxes.setter
    def resliceAxes(self, resliceAxes):
        self._resliceAxes = resliceAxes

        # TODO: update view

    def setBeam(self, beam:PlanIonBeam, referenceImage:Image3D):
        transfo_mat = vtkCommonMath.vtkMatrix4x4()
        transfo_mat.DeepCopy(self._resliceAxes)
        transfo_mat.Invert()
        posAfterInverse = transfo_mat.MultiplyPoint((beam.isocenterPosition[0], beam.isocenterPosition[1], beam.isocenterPosition[2], 1))

        self._sphereSource.SetCenter(posAfterInverse[0], posAfterInverse[1], 0)

        point2 = imageTransform3D.dicomCoordinate2iecGantry(beam, beam.isocenterPosition)
        point2 = imageTransform3D.iecGantryCoordinatetoDicom(beam, [point2[0], point2[1], point2[2] - 500])

        posAfterInverse2 = transfo_mat.MultiplyPoint((point2[0], point2[1], point2[2], 1))

        points = vtkPoints()
        points.InsertNextPoint((posAfterInverse[0], posAfterInverse[1], 0.01))
        points.InsertNextPoint((posAfterInverse2[0], posAfterInverse2[1], 0.01))

        polyLine = vtkPolyLine()
        polyLine.GetPointIds().SetNumberOfIds(2)
        for i in range(0, 2):
            polyLine.GetPointIds().SetId(i, i)

        cells = vtkCellArray()
        cells.InsertNextCell(polyLine)

        polyData = vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetLines(cells)

        self._lineMapper.SetInputData(polyData)

        self._sphereActor.SetVisibility(True)
        self._lineActor.SetVisibility(True)

        self._renderWindow.Render()


class RTPlanLayer:
    def __init__(self, renderer, renderWindow):
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._resliceAxes = None
        self._plan = None

        self._beamLayers = []

    def close(self):
        for bLayer in self._beamLayers:
            bLayer.close()

        self._beamLayers = []

        self._renderWindow.Render()

    @property
    def resliceAxes(self):
        return self._resliceAxes

    @resliceAxes.setter
    def resliceAxes(self, resliceAxes):
        self._resliceAxes = resliceAxes

        for bl in self._beamLayers:
            bl.resliceAxes = self._resliceAxes

    @property
    def plan(self) -> Optional[RTPlan]:
        return self._plan

    def setPlan(self, plan:RTPlan, referenceImage:Image3D):
        if plan is None:
            self._plan = None
            self.close()
            return
        elif self._plan == plan:
            return

        self._plan = plan

        self.close()

        for beam in plan:
            bLayer = BeamLayer(self._renderer, self._renderWindow)
            bLayer.resliceAxes = self._resliceAxes
            bLayer.setBeam(beam, referenceImage)
            self._beamLayers.append(bLayer)

        self._renderWindow.Render()