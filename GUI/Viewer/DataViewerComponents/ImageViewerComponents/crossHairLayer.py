import typing

import vtkmodules.vtkRenderingOpenGL2 #This is necessary to avoid a seg fault
import vtkmodules.vtkRenderingFreeType  #This is necessary to avoid a seg fault
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyLine, vtkCellArray, vtkPolyData
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor


class CrossHairLayer:
    def __init__(self, renderer, renderWindow):
        self._crossHairActor = vtkActor()
        self._crossHairEnabled = False
        self._crossHairMapper = vtkPolyDataMapper()
        self._position = (0, 0)
        self._renderer = renderer
        self._renderWindow = renderWindow
        self._visible = False

        colors = vtkNamedColors()

        self._crossHairActor.SetMapper(self._crossHairMapper)
        self._crossHairActor.GetProperty().SetColor(colors.GetColor3d('Tomato'))
        self._renderer.AddActor(self._crossHairActor)
        self._crossHairActor.VisibilityOff()

    def close(self):
        pass

    @property
    def position(self) -> typing.Sequence:
        return self._position

    @position.setter
    def position(self, position: typing.Sequence):
        points = vtkPoints()
        points.InsertNextPoint((position[0] - 10, position[1], 0.01))
        points.InsertNextPoint((position[0] + 10, position[1], 0.01))
        points.InsertNextPoint((position[0], position[1] - 10, 0.01))
        points.InsertNextPoint((position[0], position[1] + 10, 0.01))

        polyLine = vtkPolyLine()
        polyLine.GetPointIds().SetNumberOfIds(2)
        polyLine2 = vtkPolyLine()
        polyLine2.GetPointIds().SetNumberOfIds(2)
        for i in range(0, 2):
            polyLine.GetPointIds().SetId(i, i)
            polyLine2.GetPointIds().SetId(i, i + 2)

        cells = vtkCellArray()
        cells.InsertNextCell(polyLine)
        cells.InsertNextCell(polyLine2)

        polyData = vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetLines(cells)

        self._crossHairMapper.SetInputData(polyData)
        self._position = position

        self._renderWindow.Render()

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, visible: bool):
        self._crossHairActor.SetVisibility(visible)
        self._visible = visible
