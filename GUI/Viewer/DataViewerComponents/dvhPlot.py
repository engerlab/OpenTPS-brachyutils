from functools import partial
from typing import Union, Sequence, Optional

import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from pyqtgraph import PlotWidget, mkPen, PlotCurveItem

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.dvh import DVH
from Core.Data.roiContour import ROIContour
from Core.event import Event
from GUI.Viewer.DataForViewer.ROIContourForViewer import ROIContourForViewer
from GUI.Viewer.DataForViewer.ROIMaskForViewer import ROIMaskForViewer


class DVHViewer(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.doseChangeEvent = Event(object)

        self._dose = None
        self._rois = []
        self._dvhs = []
        self._partialVisibilityhandlers = []

        self._mainLayout = QVBoxLayout()
        self.setLayout(self._mainLayout)

        self._dvhPlot = DVHPlot(self)
        self._mainLayout.addWidget(self._dvhPlot)

    @property
    def dose(self) -> Optional[DoseImage]:
        return self._dose

    @dose.setter
    def dose(self, dose:DoseImage):
        if dose==self._dose:
            return

        self._dose = dose

        for dvh in self._dvhs:
            dvh.dose = dose
            dvh.computeDVH()

        self.doseChangeEvent.emit(self._dose)

    @property
    def rois(self) -> Sequence[Union[ROIMask, ROIContour]]:
        return [roi for roi in self._rois]

    def appendROI(self, roi:Union[ROIMask, ROIContour]):
        # TODO a factory in DataForViewer would be nice because this small piece of code is often duplicated
        if isinstance(roi, ROIMask):
            roiForViewer = ROIMaskForViewer(roi)
        elif isinstance(roi, ROIContour):
            roiForViewer = ROIContourForViewer(roi)
        else:
            raise ValueError("ROI must be an instance of ROIMask or a ROIContour")

        if not roiForViewer.visible:
            return

        partialHandler = partial(self._handleROIVisibility, roi)
        self._partialVisibilityhandlers.append(partialHandler)
        roiForViewer.visibleChangedSignal.connect(partialHandler)

        self._rois.append(roi)

        dvh = DVH(roi)
        self._dvhs.append(dvh)
        self._dvhPlot.appendDVH(dvh, roi)

        if not (self._dose is None):
            dvh.dose = self.dose
            dvh.computeDVH()

    def _handleROIVisibility(self, roi, visibility):
        if not visibility:
            self.removeROI(roi)

    def removeROI(self, roi:Union[ROIMask, ROIContour]):
        partialHandler = self._partialVisibilityhandlers[self._rois.index(roi)]
        self._partialVisibilityhandlers.remove(partialHandler)

        # TODO a factory in DataForViewer would be nice because this small piece of code is often duplicated
        if isinstance(roi, ROIMask):
            roiForViewer = ROIMaskForViewer(roi)
        elif isinstance(roi, ROIContour):
            roiForViewer = ROIContourForViewer(roi)
        else:
            raise ValueError("ROI must be an instance of ROIMask or a ROIContour")
        roiForViewer.visibleChangedSignal.disconnect(partialHandler)

        dvh = self._dvhs[self._rois.index(roi)]
        self._dvhPlot.removeDVH(dvh)
        self._dvhs.remove(dvh)

        self._rois.remove(roi)

    def clear(self):
        for roi in self._rois:
            self.removeROI(roi)
        self._dose = None


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

    @property
    def DVHs(self) -> Sequence[DVH]:
        return [dvh for dvh in self._dvhs]

    def appendDVH(self, dvh:DVH, referenceROI:Union[ROIContour, ROIMask]):
        self._dvhs.append(dvh)
        self._referenceROIs.append(referenceROI)

        curve = DVHCurve(dvh, referenceROI, self)
        self._curves.append(curve)

        self.addItem(curve.curve)

    def removeDVH(self, dvh:DVH):
        self._referenceROIs.remove(self._referenceROIs[self._dvhs.index(dvh)])
        curve = self._curves[self._dvhs.index(dvh)]
        curve.clear()
        self._curves.remove(curve)
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

    def clear(self):
        self.curve.setData(None, None)
        self._dvh.dataUpdatedEvent.disconnect(self._setCurveData)
        self._referenceROI.nameChangedSignal.disconnect(self._setCurveData)
        self._referenceROI.colorChangedSignal.disconnect(self._setCurveData)
        self.curve.clear() # TODO does nothing, apparently...
