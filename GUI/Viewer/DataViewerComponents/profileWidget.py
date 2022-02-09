import typing
from math import sqrt

import numpy as np
from vtkmodules.vtkInteractionWidgets import vtkLineWidget2

from Core.event import Event


class ProfileWidget:
    def __init__(self, renderer, renderWindow):
        self.lineWidgeEnabledSignal = Event(bool)

        self._lineWidget = vtkLineWidget2()
        self._lineWidgetCallback = None
        self._lineWidgetEnabled = False
        self._primaryReslice = None
        self._renderer = renderer
        self._renderWindow = renderWindow

        self._lineWidget.SetCurrentRenderer(self._renderer)

    @property
    def enabled(self) -> bool:
        return self._lineWidgetEnabled

    @enabled.setter
    def enabled(self, enabled: bool):
        if enabled == self._lineWidgetEnabled:
            return

        if enabled:
            self._lineWidget.AddObserver("InteractionEvent", self.onprofileWidgetInteraction)
            self._lineWidget.AddObserver("EndInteractionEvent", self.onprofileWidgetInteraction)
            self._lineWidget.SetInteractor(self._renderWindow.GetInteractor())
            self._lineWidget.On()
            self._lineWidget.GetLineRepresentation().SetLineColor(1, 0, 0)
            self._lineWidgetEnabled = True
        else:
            self._lineWidget.Off()
            self._lineWidgetEnabled = False
            self._renderWindow.Render()

        self.lineWidgeEnabledSignal.emit(self._lineWidgetEnabled)

    @property
    def callback(self):
        return self._lineWidgetCallback

    @callback.setter
    def callback(self, method):
        self._lineWidgetCallback = method

    @property
    def primaryReslice(self):
        return self._primaryReslice

    @primaryReslice.setter
    def primaryReslice(self, reslice):
        if not self._primaryReslice is None:
            self._primaryReslice.RemoveObserver("EndEvent", self.onprofileWidgetInteraction)

        self._primaryReslice = reslice
        self._primaryReslice.AddObserver("EndEvent", self.onprofileWidgetInteraction)

    def setInitialPosition(self, worldPos: typing.Sequence):
        self._lineWidget.GetLineRepresentation().SetPoint1WorldPosition((worldPos[0], worldPos[1], 0.01))
        self._lineWidget.GetLineRepresentation().SetPoint2WorldPosition((worldPos[0], worldPos[1], 0.01))

    def onprofileWidgetInteraction(self, obj, event):
        if not self.enabled:
            return

        point1 = self._lineWidget.GetLineRepresentation().GetPoint1WorldPosition()
        point2 = self._lineWidget.GetLineRepresentation().GetPoint2WorldPosition()

        matrix = self._primaryReslice.GetResliceAxes()
        point1 = matrix.MultiplyPoint((point1[0], point1[1], 0, 1))
        point2 = matrix.MultiplyPoint((point2[0], point2[1], 0, 1))

        num = 1000
        points0 = np.linspace(point1[0], point2[0], num)
        points1 = np.linspace(point1[1], point2[1], num)
        points2 = np.linspace(point1[2], point2[2], num)
        data = np.array(points1)

        imageData = self._primaryReslice.GetInput(0)
        for i, p0 in enumerate(points0):
            ind = [0, 0, 0]
            imageData.TransformPhysicalPointToContinuousIndex((p0, points1[i], points2[i]), ind)
            data[i] = imageData.GetScalarComponentAsFloat(int(ind[0]), int(ind[1]), int(ind[2]), 0)

        x = np.linspace(0, sqrt((point2[0] - point1[0]) * (point2[0] - point1[0]) + (point2[1] - point1[1]) * (
                    point2[1] - point1[1]) + (point2[2] - point1[2]) * (point2[2] - point1[2])), num)
        self._lineWidgetCallback(x, data)
