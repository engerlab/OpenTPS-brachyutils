from typing import Sequence

import numpy as np
import vtkmodules.vtkCommonCore as vtkCommonCore
from matplotlib import pyplot as plt


def fusionLT(range:Sequence[float], opacity:float, colormap:str):
    table = vtkCommonCore.vtkLookupTable()
    table.SetRange(range[0], range[1])  # image intensity range
    table.SetValueRange(0.0, 1.0)  # from black to white
    table.SetSaturationRange(0.0, 0.0)  # no color saturation
    table.SetRampToLinear()

    cm = plt.cm.get_cmap(colormap)
    linInd = list(np.arange(0, 1.01, 0.01))

    table.SetNumberOfTableValues(len(linInd))
    for i, ind in enumerate(linInd):
        cmVal = cm(ind)
        if i==0:
            table.SetTableValue(i, (cmVal[0], cmVal[1], cmVal[2], 0))
        else:
            table.SetTableValue(i, (cmVal[0], cmVal[1], cmVal[2], opacity))

    table.SetBelowRangeColor(0, 0, 0, 0)
    table.SetUseBelowRangeColor(True)
    table.SetAboveRangeColor(1.0000, 0, 0, opacity)
    table.SetUseAboveRangeColor(True)
    table.Build()

    return table
def grayLT(range):
    table = vtkCommonCore.vtkLookupTable()
    table.SetRange(range[0], range[1])  # image intensity range
    table.SetValueRange(0.0, 1.0)  # from black to white
    table.SetSaturationRange(0.0, 0.0)  # no color saturation
    table.SetRampToLinear()
    table.Build()

    return table