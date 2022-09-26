import typing
from math import sqrt

import numpy as np
from pyqtgraph import mkPen
from vtkmodules.vtkInteractionWidgets import vtkLineWidget2

from opentps.core import Event
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.contourLayer import ContourLayer
from opentps.gui.viewer.dataViewerComponents.imageViewerComponents.primaryImage3DLayer import PrimaryImage3DLayer


class ProfileWidget:
    class ProfileWidgetCallback:
        def __init__(self):
            self._setPrimaryImageData = lambda *args, **kwargs: None
            self._setSecondaryImageData = lambda *args, **kwargs: None
            self._setContourData = lambda *args, **kwargs: None

        @property
        def setPrimaryImageData(self):
            return self._setPrimaryImageData

        @setPrimaryImageData.setter
        def setPrimaryImageData(self, func):
            self._setPrimaryImageData = func

        @property
        def setSecondaryImageData(self):
            return self._setSecondaryImageData

        @setSecondaryImageData.setter
        def setSecondaryImageData(self, func):
            self._setSecondaryImageData = func

        @property
        def setContourData(self):
            return self._setContourData

        @setContourData.setter
        def setContourData(self, func):
            self._setContourData = func

    def __init__(self, renderer, renderWindow):
        self.lineWidgeEnabledSignal = Event(bool)

        self._lineWidget = vtkLineWidget2()
        self._lineWidgetCallback = None
        self._lineWidgetEnabled = False
        self._primaryLayer = None
        self._secondaryLayer = None
        self._contourLayer = None
        self._renderer = renderer
        self._renderWindow = renderWindow

        self._lineWidget.SetCurrentRenderer(self._renderer)
        self._lineWidget.AddObserver("InteractionEvent", self.onProfileWidgetInteraction)
        self._lineWidget.AddObserver("EndInteractionEvent", self.onProfileWidgetInteraction)
        self._lineWidget.SetInteractor(self._renderWindow.GetInteractor())

    @property
    def enabled(self) -> bool:
        return self._lineWidgetEnabled

    @enabled.setter
    def enabled(self, enabled: bool):
        if enabled == self._lineWidgetEnabled:
            return

        if enabled:
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
    def primaryLayer(self):
        return self._primaryLayer

    @primaryLayer.setter
    def primaryLayer(self, layer):
        self._primaryLayer = layer

        if isinstance(self._primaryLayer, PrimaryImage3DLayer):
            if not self._primaryLayer.image is None:
                self._primaryLayer._reslice.RemoveObserver(self._endEventObserver)

            self._endEventObserver = self._primaryLayer._reslice.AddObserver("EndEvent", self.onProfileWidgetInteraction)

    @property
    def secondaryLayer(self):
        return self._secondaryLayer

    @secondaryLayer.setter
    def secondaryLayer(self, layer):
        self._secondaryLayer = layer

    @property
    def contourLayer(self):
        return self._secondaryLayer

    @contourLayer.setter
    def contourLayer(self, layer):
        self._contourLayer = layer

    def setInitialPosition(self, worldPos: typing.Sequence):
        self._lineWidget.GetLineRepresentation().SetPoint1WorldPosition((worldPos[0], worldPos[1], 0.01))
        self._lineWidget.GetLineRepresentation().SetPoint2WorldPosition((worldPos[0], worldPos[1], 0.01))

    def onProfileWidgetInteraction(self, obj, event):
        if not self.enabled:
            return

        point1 = self._lineWidget.GetLineRepresentation().GetPoint1WorldPosition()
        point2 = self._lineWidget.GetLineRepresentation().GetPoint2WorldPosition()

        if point1[1]==point1[2]==point2[1]==point2[2]:
            return

        matrix = self._primaryLayer.resliceAxes
        point1 = matrix.MultiplyPoint((point1[0], point1[1], 0, 1))
        point2 = matrix.MultiplyPoint((point2[0], point2[1], 0, 1))

        x, y = self._resliceLayerDataBewteenTwoPoints(self._primaryLayer, point1, point2)
        self._lineWidgetCallback.setPrimaryImageData(x, y, name=self._layerImageName(self._primaryLayer))

        x, y = self._resliceLayerDataBewteenTwoPoints(self._secondaryLayer, point1, point2)
        self._lineWidgetCallback.setSecondaryImageData(x, y, name=self._layerImageName(self._secondaryLayer))

        contourNames = [contour.name for contour in self._contourLayer.contours]
        contourData = self._resliceContoursBetweenTwoPoints(self._contourLayer, point1, point2)
        pen = [mkPen(color=contour.color, width=1) for contour in self._contourLayer.contours]
        self._lineWidgetCallback.setContourData(contourData, name=contourNames, pen=pen)

    def _resliceLayerDataBewteenTwoPoints(self, layer, point1, point2):
        if layer.image is None:
            return ([0, 0], [0, 0])

        num = 1000
        points0 = np.linspace(point1[0], point2[0], num)
        points1 = np.linspace(point1[1], point2[1], num)
        points2 = np.linspace(point1[2], point2[2], num)
        data = np.array(points1)

        x = np.linspace(0, sqrt((point2[0] - point1[0]) * (point2[0] - point1[0]) + (point2[1] - point1[1]) * (
                point2[1] - point1[1]) + (point2[2] - point1[2]) * (point2[2] - point1[2])), num)

        for i, p0 in enumerate(points0):
            data[i] = layer.resliceDataFromPhysicalPoint((p0, points1[i], points2[i]))

        return (x, data)

    def _layerImageName(self, layer):
        if layer.image is None:
            return None

        return layer.image.name


    def _resliceContoursBetweenTwoPoints(self, layer:ContourLayer, point1:typing.Sequence[float], point2:typing.Sequence[float]):
        contours = layer.contours

        res = []
        if len(contours)<=0:
            for contour in contours:
                res.append(([0, 0], [0, 0]))
            return res

        num = 1000
        points0 = np.linspace(point1[0], point2[0], num)
        points1 = np.linspace(point1[1], point2[1], num)
        points2 = np.linspace(point1[2], point2[2], num)


        data = np.zeros((len(contours), num))
        x = np.linspace(0, sqrt((point2[0] - point1[0]) * (point2[0] - point1[0]) + (point2[1] - point1[1]) * (
                point2[1] - point1[1]) + (point2[2] - point1[2]) * (point2[2] - point1[2])), num)


        for i, p0 in enumerate(points0):
            contoursData = layer.resliceDataFromPhysicalPoint((p0, points1[i], points2[i]))
            for c, contour in enumerate(contours):
                data[c, i] = -10000+contoursData[c]*20000

        for c, contour in enumerate(contours):
            res.append((x, data[c, :]))

        return res
