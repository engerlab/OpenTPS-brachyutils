from typing import Union

import numpy as np
from PyQt5.QtWidgets import QApplication
from pyqtgraph import PlotWidget, mkPen, PlotCurveItem

from Core.Data.Images.roiMask import ROIMask
from Core.Data.dvh import DVH
from Core.Data.roiContour import ROIContour


class DVHPlot(PlotWidget):
    def __init__(self, parent):
        PlotWidget.__init__(self, parent=parent)

        self.getPlotItem().setContentsMargins(5, 0, 20, 5)
        self.setBackground('k')
        self.setTitle("DVH")
        self.setLabel('left', 'Volume (%)')
        self.setLabel('bottom', 'Dose (Gy)')
        self.showGrid(x=True, y=True)
        self.setXRange(0, 100, padding=0)
        self.setYRange(0, 100, padding=0)

        self._parent = parent

        self._dvhs = []
        self._referenceROIs = []
        self._curves = []

    def appendDVH(self, dvh:DVH, referenceROI:Union[ROIContour, ROIMask]):
        self._dvhs.append(dvh)
        self._referenceROIs.append(referenceROI)

        curve = DVHCurve(dvh, referenceROI, self)
        self._curves.append(curve)

        self.addItem(curve.curve)


    def removeDVH(self, dvh:DVH):
        self._referenceROIs.remove(self._referenceROIs[self._dvhs.index(dvh)])
        self._curves.remove(self._curves[self._dvhs.index(dvh)])
        self._dvhs.remove(dvh)

class DVHCurve:
    def __init__(self, dvh:DVH, referenceROI:Union[ROIContour, ROIMask], parent=None):
        self._dvh = dvh
        self._referenceROI = referenceROI
        self._parent = parent

        self.curve = PlotCurveItem(np.array([]), np.array([]))

        self._dvh.dataUpdatedEvent.connect(self._setCurveData)
        self._referenceROI.nameChangedSignal.connect(self._setCurveData)
        self._referenceROI.colorChangedSignal.connect(self._setCurveData)

        self._setCurveData()

    def _setCurveData(self, *args):
        mycolor = (self._referenceROI.color[2], self._referenceROI.color[1], self._referenceROI.color[0])
        pen = mkPen(color=mycolor, width=1)

        dose, volume = self._dvh.histogram
        self.curve.setData(dose, volume, pen=pen, name=self._referenceROI.name)

        # To force update the plot
        QApplication.processEvents()
