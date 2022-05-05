
import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersSources import vtkSphereSource, vtkLineSource
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

from Core.Data.Images.image3D import Image3D
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.rtPlan import RTPlan
from Core.Processing.ImageProcessing import imageTransform3D


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

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(self._lineSource.GetOutputPort())

        self._lineActor = vtkActor()
        self._lineActor.SetMapper(mapper)
        self._lineActor.GetProperty().SetColor(colors.GetColor3d("Fuchsia"))
        self._lineActor.SetVisibility(False)

        renderer.AddActor(self._lineActor)

    def close(self):
        self._sphereActor.SetVisibility(False)
        self._lineActor.SetVisibility(False)

        self._renderer.RemoveActor(self._sphereActor)
        self._renderer.RemoveActor(self._lineActor)

    def setBeam(self, beam:PlanIonBeam, referenceImage:Image3D):
        print(beam.isocenterPosition)

        self._sphereSource.SetCenter(beam.isocenterPosition[0], beam.isocenterPosition[1], beam.isocenterPosition[2])

        point2 = imageTransform3D.iecGantryCoordinatetoDicom(referenceImage, beam, beam.isocenterPosition)
        referenceImage2 = imageTransform3D.iecGantryToDicom(referenceImage, beam)
        point2 = imageTransform3D.iecGantryCoordinatetoDicom(referenceImage2, beam, [point2[0], point2[1], referenceImage.origin[2]])
        self._lineSource.SetPoint1(point2)
        self._lineSource.SetPoint2(beam.isocenterPosition)

        self._sphereActor.SetVisibility(True)
        self._lineActor.SetVisibility(True)

        self._renderWindow.Render()


class RTPlanLayer:
    def __init__(self, renderer, renderWindow):
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._resliceAxes = None

        self._beamLayers = []

    def close(self):
        for bLayer in self._beamLayers:
            bLayer.close()

        self._beamLayers = []

    @property
    def resliceAxes(self):
        return self._resliceAxes

    @resliceAxes.setter
    def resliceAxes(self, resliceAxes):
        self._resliceAxes = resliceAxes

    def setPlan(self, plan:RTPlan, referenceImage:Image3D):
        if plan is None:
            self.close()
            return

        for beam in plan:
            bLayer = BeamLayer(self._renderer, self._renderWindow)
            bLayer.setBeam(beam, referenceImage)
            self._beamLayers.append(bLayer)

        self._renderWindow.Render()