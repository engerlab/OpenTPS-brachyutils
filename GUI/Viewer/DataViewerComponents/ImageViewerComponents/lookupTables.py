from typing import Sequence, Tuple

import numpy as np
import vtkmodules.vtkCommonCore as vtkCommonCore
from matplotlib import pyplot as plt
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkRenderingCore import vtkColorTransferFunction


def fusionLT(range:Sequence[float], opacity:float, colormap:str) -> vtkCommonCore.vtkLookupTable:
    table = vtkCommonCore.vtkLookupTable()
    table.SetRange(range[0], range[1])  # image intensity range
    table.SetValueRange(0.0, 1.0)  # from black to white
    table.SetSaturationRange(0.0, 0.0)  # no color saturation
    table.SetRampToLinear()

    cm = plt.cm.get_cmap(colormap)
    linInd = list(np.arange(0, 1.01, 0.01))

    table.SetNumberOfTableValues(len(linInd))
    LastCMVal = (0, 0, 0)
    for i, ind in enumerate(linInd):
        cmVal = cm(ind)
        LastCMVal = cmVal
        if i==0:
            table.SetTableValue(i, (cmVal[0], cmVal[1], cmVal[2], 0))
        else:
            table.SetTableValue(i, (cmVal[0], cmVal[1], cmVal[2], opacity))

    table.SetBelowRangeColor(0, 0, 0, 0)
    table.SetUseBelowRangeColor(True)
    table.SetAboveRangeColor(LastCMVal[0], LastCMVal[1], LastCMVal[2], opacity)
    table.SetUseAboveRangeColor(True)
    table.Build()

    return table

def grayLT(range) -> vtkCommonCore.vtkLookupTable:
    table = vtkCommonCore.vtkLookupTable()
    table.SetRange(range[0], range[1])  # image intensity range
    table.SetTableRange(range[0], range[1])  # image intensity range
    table.SetValueRange(0.0, 1.0)  # from black to white
    table.SetSaturationRange(0.0, 0.0)  # no color saturation
    table.SetRampToLinear()
    table.SetAlpha(1.)
    table.SetAboveRangeColor(1., 1., 1., 1.)
    table.SetBelowRangeColor(0., 0., 0., 1.)
    table.SetUseAboveRangeColor(True)
    table.SetUseBelowRangeColor(True)
    table.Build()

    return table


def fusionLTTo3DLT(lt:vtkCommonCore.vtkLookupTable) -> Tuple[vtkColorTransferFunction, vtkPiecewiseFunction, vtkPiecewiseFunction]:
    rangeVal = lt.GetRange()

    volumeColor = vtkColorTransferFunction()
    volumeScalarOpacity = vtkPiecewiseFunction()
    volumeGradientOpacity = vtkPiecewiseFunction()

    volumeScalarOpacity.AddPoint(rangeVal[0], 0)
    volumeScalarOpacity.AddPoint((rangeVal[0]+rangeVal[1])/.2, 0.25)
    volumeScalarOpacity.AddPoint(rangeVal[1], 1.)

    volumeGradientOpacity.AddPoint(rangeVal[0], 0.25)
    volumeGradientOpacity.AddPoint((rangeVal[0]+rangeVal[1])/2, 0.5)
    volumeGradientOpacity.AddPoint(rangeVal[1], 1.)

    tableVals = np.linspace(rangeVal[0], rangeVal[1], lt.GetNumberOfTableValues())
    for i in range(lt.GetNumberOfTableValues()):
        tbVal = lt.GetTableValue(i)
        volumeColor.AddRGBPoint(tableVals[i], tbVal[0], tbVal[1], tbVal[2])

    return volumeColor, volumeScalarOpacity, volumeGradientOpacity
