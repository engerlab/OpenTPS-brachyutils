from typing import Sequence, Tuple

import numpy as np
import vtkmodules.vtkCommonCore as vtkCommonCore
from matplotlib import pyplot as plt
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkRenderingCore import vtkColorTransferFunction


def uniqueColorLT(threshold:float, opacity:float, color:Sequence[float]) -> vtkCommonCore.vtkLookupTable:
    table = vtkCommonCore.vtkLookupTable()
    table.SetRange(threshold-1., threshold)  # image intensity range
    table.SetValueRange(0.0, 1.0)  # from black to white
    table.SetSaturationRange(0.0, 0.0)  # no color saturation
    table.SetRampToLinear()

    table.SetNumberOfTableValues(2)
    table.SetTableValue(0, (0, 0, 0, 0))
    table.SetTableValue(1, (color[0], color[1], color[2], opacity))

    table.SetBelowRangeColor(0, 0, 0, 0)
    table.SetUseBelowRangeColor(True)
    table.SetAboveRangeColor(color[0], color[1], color[2], opacity)
    table.SetUseAboveRangeColor(True)
    table.Build()

    return table

def uniqueColorLTTo3DLT(lt:vtkCommonCore.vtkLookupTable) -> Tuple[vtkColorTransferFunction, vtkPiecewiseFunction, vtkPiecewiseFunction]:
    rangeVal = lt.GetRange()
    opacity = lt.GetOpacity(rangeVal[1])

    volumeColor = vtkColorTransferFunction()
    volumeScalarOpacity = vtkPiecewiseFunction()
    volumeGradientOpacity = vtkPiecewiseFunction()

    volumeScalarOpacity.AddPoint(rangeVal[0], 0.)
    volumeScalarOpacity.AddPoint(rangeVal[1], opacity)

    volumeGradientOpacity.AddPoint(rangeVal[0], 0.)
    volumeGradientOpacity.AddPoint(rangeVal[1], opacity)

    tableVals = np.linspace(rangeVal[0], rangeVal[1], lt.GetNumberOfTableValues())
    for i in range(lt.GetNumberOfTableValues()):
        tbVal = lt.GetTableValue(i)
        volumeColor.AddRGBPoint(tableVals[i], tbVal[0], tbVal[1], tbVal[2])

    return volumeColor, volumeScalarOpacity, volumeGradientOpacity


def fusionLT(range:Sequence[float], opacity:float, colormap:str) -> vtkCommonCore.vtkLookupTable:
    table = vtkCommonCore.vtkLookupTable()
    table.SetRange(range[0], range[1])  # image intensity range
    table.SetValueRange(0.0, 1.0)  # from black to white
    table.SetSaturationRange(0.0, 0.0)  # no color saturation
    table.SetRampToLinear()
    cm = plt.get_cmap(colormap)
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
    opacity0 = lt.GetOpacity(0)
    opacity1 = lt.GetOpacity(1)

    volumeColor = vtkColorTransferFunction()
    volumeScalarOpacity = vtkPiecewiseFunction()
    volumeGradientOpacity = vtkPiecewiseFunction()

    volumeScalarOpacity.AddPoint(rangeVal[0], opacity0)
    volumeScalarOpacity.AddPoint((rangeVal[0]+rangeVal[1])/.2, opacity0)
    volumeScalarOpacity.AddPoint(3*(rangeVal[0] + rangeVal[1]) /4. , opacity1/2.)
    volumeScalarOpacity.AddPoint(rangeVal[1], opacity1)

    volumeGradientOpacity.AddPoint(rangeVal[0], opacity1)
    volumeGradientOpacity.AddPoint((rangeVal[0]+rangeVal[1])/2, opacity1/4.)
    volumeGradientOpacity.AddPoint(3*(rangeVal[0] + rangeVal[1]) /4. , opacity1/2.)
    volumeGradientOpacity.AddPoint(rangeVal[1], opacity1)

    tableVals = np.linspace(rangeVal[0], rangeVal[1], lt.GetNumberOfTableValues())
    for i in range(lt.GetNumberOfTableValues()):
        tbVal = lt.GetTableValue(i)
        volumeColor.AddRGBPoint(tableVals[i], tbVal[0], tbVal[1], tbVal[2])

    return volumeColor, volumeScalarOpacity, volumeGradientOpacity

def ct3DLT() -> Tuple[vtkColorTransferFunction, vtkPiecewiseFunction, vtkPiecewiseFunction]:
    volumeColor = vtkColorTransferFunction()
    volumeScalarOpacity = vtkPiecewiseFunction()
    volumeGradientOpacity = vtkPiecewiseFunction()

    volumeColor.AddRGBPoint(-1000, 0.0, 0.0, 0.0)
    volumeColor.AddRGBPoint(-500, 240.0/255.0, 184.0/255.0, 160.0/255.0)
    volumeColor.AddRGBPoint(0, 232/255, 147/255, 132/255)
    volumeColor.AddRGBPoint(500, 1.0, 1.0, 240.0 / 255.0)
    volumeColor.AddRGBPoint(700,  242/255, 220/255, 172/255)
    volumeColor.AddRGBPoint(1800, 173/255, 166/255, 166/255)
    volumeColor.AddRGBPoint(2500, 237/255, 171/255, 64/255)

    volumeScalarOpacity.AddPoint(-1000, 0.00)
    volumeScalarOpacity.AddPoint(-500, 0.05)
    volumeScalarOpacity.AddPoint(-200, 0.5)
    volumeScalarOpacity.AddPoint(-100, 0.85)
    volumeScalarOpacity.AddPoint(0, 0.85)
    volumeScalarOpacity.AddPoint(500, 0.85)
    volumeScalarOpacity.AddPoint(700, 0.85)

    volumeGradientOpacity.AddPoint(-1000, 0.0)
    volumeGradientOpacity.AddPoint(-500, 0.0)
    volumeGradientOpacity.AddPoint(0, 0.6)
    volumeGradientOpacity.AddPoint(500, 0.85)

    return volumeColor, volumeScalarOpacity, volumeGradientOpacity