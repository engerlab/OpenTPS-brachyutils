from functools import partial
from typing import Union, Sequence, Optional

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from pyqtgraph import PlotWidget, mkPen, PlotCurveItem, SignalProxy, TextItem

from opentps.core.data.images import DoseImage
from opentps.core.data.images import ROIMask
from opentps.core.data import DVH
from opentps.core.data._roiContour import ROIContour
from opentps.core import Event
from opentps.gui.viewer.dataForViewer.ROIContourForViewer import ROIContourForViewer
from opentps.gui.viewer.dataForViewer.ROIMaskForViewer import ROIMaskForViewer


class DVHViewer(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.doseChangeEvent = Event(object)
        self.dose2ChangeEvent = Event(object)

        self._dose = None
        self._rois = []
        self._dvhs = []
        self._dose2 = None
        self._dvhs2 = []
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
            if self._dose is None:
                self._dvhPlot.removeDVH(dvh)
            else:
                dvh.dose = dose
                dvh.computeDVH()

        self.doseChangeEvent.emit(self._dose)

    @property
    def dose2(self) -> Optional[DoseImage]:
        return self._dose2

    @dose2.setter
    def dose2(self, dose: DoseImage):
        if dose == self._dose2:
            return

        self._dose2 = dose

        for dvh in self._dvhs2:
            if self._dose2 is None:
                self._dvhPlot.removeDVH(dvh)
            else:
                dvh.dose = dose
                dvh.computeDVH()

        self.dose2ChangeEvent.emit(self._dose2)

    @property
    def rois(self) -> Sequence[Union[ROIMask, ROIContour]]:
        return [roi for roi in self._rois]

    def appendROI(self, roi:Union[ROIMask, ROIContour]):
        if roi in self._rois:
            return

        # TODO a factory in dataForViewer would be nice because this small piece of code is often duplicated
        if isinstance(roi, ROIMask):
            roiForViewer = ROIMaskForViewer(roi)
        elif isinstance(roi, ROIContour):
            roiForViewer = ROIContourForViewer(roi)
        else:
            raise ValueError("ROI must be an instance of ROIMask or a ROIContour")

        if not roiForViewer.visible:
            return

        partialHandler = partial(self._handleROIVisibility, roi)
        roiForViewer.visibleChangedSignal.connect(partialHandler)

        dvh = DVH(roi)
        dvh2 = DVH(roi)

        self._rois.append(roi)
        self._partialVisibilityhandlers.append(partialHandler)

        self._dvhs.append(dvh)
        self._dvhPlot.appendDVH(dvh, roi, style=Qt.SolidLine)
        self._dvhs2.append(dvh2)
        self._dvhPlot.appendDVH(dvh2, roi, style=Qt.DashLine)

        if not (self._dose is None):
            dvh.dose = self._dose
            dvh.computeDVH()

        if not (self._dose2 is None):
            dvh2.dose = self._dose2
            dvh2.computeDVH()

    def _handleROIVisibility(self, roi, visibility):
        if not visibility:
            self.removeROI(roi)

    def removeROI(self, roi:Union[ROIMask, ROIContour]):
        partialHandler = self._partialVisibilityhandlers[self._rois.index(roi)]
        roiIndex = self._rois.index(roi)
        dvh = self._dvhs[roiIndex]

        # TODO a factory in dataForViewer would be nice because this small piece of code is often duplicated
        if isinstance(roi, ROIMask):
            roiForViewer = ROIMaskForViewer(roi)
        elif isinstance(roi, ROIContour):
            roiForViewer = ROIContourForViewer(roi)
        else:
            raise ValueError("ROI must be an instance of ROIMask or a ROIContour")

        roiForViewer.visibleChangedSignal.disconnect(partialHandler)

        self._dvhPlot.removeDVH(dvh)
        self._rois.remove(roi)

        dvh2Exists = len(self._dvhs2) > 0
        if dvh2Exists:
            dvh2 = self._dvhs2[roiIndex]
            self._dvhPlot.removeDVH(dvh2)
            self._dvhs2.remove(dvh2)
        self._dvhs.remove(dvh)

        self._partialVisibilityhandlers.remove(partialHandler)

    def clear(self):
        for roi in self._rois:
            self.removeROI(roi)
        self._dose = None
        self._dose2 = None


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

    def appendDVH(self, dvh:DVH, referenceROI:Union[ROIContour, ROIMask], style=Qt.SolidLine):
        curve = DVHCurve(dvh, referenceROI, self, style=style)
        self.addItem(curve.curve)
        self.addItem(curve.dvhLabel)

        self._referenceROIs.append(referenceROI)
        self._dvhs.append(dvh)
        self._curves.append(curve)

    def removeDVH(self, dvh:DVH):
        curve = self._curves[self._dvhs.index(dvh)]
        curve.clear()

        self._referenceROIs.remove(self._referenceROIs[self._dvhs.index(dvh)])
        self._curves.remove(curve)
        self._dvhs.remove(dvh)

    def clear(self):
        for curve in self._curves:
            curve.clear()

class DVHCurve:
    def __init__(self, dvh:DVH, referenceROI:Union[ROIContour, ROIMask], parent=None, style=Qt.SolidLine):
        self._dvh = dvh
        self._referenceROI = referenceROI
        self._parent = parent
        self._style = style

        self.curve = PlotCurveItem(np.array([]), np.array([]), style=style)

        self._dvh.dataUpdatedEvent.connect(self._setCurveData)
        self._referenceROI.nameChangedSignal.connect(self._setCurveData)
        self._referenceROI.colorChangedSignal.connect(self._setCurveData)

        self._viewer_DVH_proxy = SignalProxy(self._parent.scene().sigMouseMoved, rateLimit=120, slot=self._handleMouseMoved)
        self.dvhLabel = TextItem("", color=(255, 255, 255), fill=(0, 0, 0, 250), anchor=(0, 1))
        self.dvhLabel.hide()

        self._setCurveData()

    def _setCurveData(self, *args):
        mycolor = (self._referenceROI.color[0], self._referenceROI.color[1], self._referenceROI.color[2])
        pen = mkPen(color=mycolor, width=2, style=self._style)

        dose, volume = self._dvh.histogram
        self.curve.setData(dose, volume, pen=pen, name=self._referenceROI.name)
        self.curve.setData(dose, volume, pen=pen, name=self._referenceROI.name)
        # To force update the plot
        QApplication.processEvents()

    def clear(self):
        self.curve.setData(None, None)
        self._dvh.dataUpdatedEvent.disconnect(self._setCurveData)
        self._referenceROI.nameChangedSignal.disconnect(self._setCurveData)
        self._referenceROI.colorChangedSignal.disconnect(self._setCurveData)
        self.curve.clear() # TODO does nothing, apparently...

    def _handleMouseMoved(self, evt):
        self.dvhLabel.hide()

        mycolor = (self._referenceROI.color[0], self._referenceROI.color[1], self._referenceROI.color[2])

        if self.curve.sceneBoundingRect().contains(evt[0]):
            mousePoint = self._parent.getViewBox().mapSceneToView(evt[0])
            for item in self.curve.scene().items():
                if isinstance(item, PlotCurveItem):
                    data = item.getData()

                    if data[0] is None or len(data[0])<=0:
                        continue

                    y, y2 = np.interp([mousePoint.x(), mousePoint.x() * 1.01], data[0], data[1])
                    # if item.mouseShape().contains(mousePoint):
                    # check if mouse.y is close to f(mouse.x)
                    if abs(y - mousePoint.y()) < 2.0 + abs(y2 - y):  # abs(y2-y) is to increase the distance in high gradient
                        self.dvhLabel.setHtml("<b><font color='#" + "{:02x}{:02x}{:02x}".format(mycolor[0],
                                                                                                mycolor[1],
                                                                                                mycolor[2]) + "'>" + \
                                              item.name() + ":</font></b>" + \
                                                      "<br>D95 = {:.1f} Gy".format(self._dvh.D95) + \
                                                      "<br>D5 = {:.1f} Gy".format(self._dvh.D5) + \
                                                      "<br>Dmean = {:.1f} Gy".format(self._dvh.Dmean))
                        self.dvhLabel.setPos(mousePoint)
                        if (mousePoint.x() < 50 and mousePoint.y() < 50):
                            self.dvhLabel.setAnchor((0, 1))
                        elif (mousePoint.x() < 50 and mousePoint.y() >= 50):
                            self.dvhLabel.setAnchor((0, 0))
                        elif (mousePoint.x() >= 50 and mousePoint.y() < 50):
                            self.dvhLabel.setAnchor((1, 1))
                        elif (mousePoint.x() >= 50 and mousePoint.y() >= 50):
                            self.dvhLabel.setAnchor((1, 0))
                        self.dvhLabel.show()
                        break

class DVHBand:
    def __init__(self, dvh:DVH, referenceROI:Union[ROIContour, ROIMask], parent=None):
        self._dvh = dvh
        self._referenceROI = referenceROI
        self._parent = parent

        self.volume_low = []
        self.volume_high = []
        self.nominalDVH = []
        self.ROIDisplayColor = []
        self.Dmean = [0, 0]
        self.D98 = [0, 0]
        self.D95 = [0, 0]
        self.D50 = [0, 0]
        self.D5 = [0, 0]
        self.D2 = [0, 0]

    def compute_metrics(self):
        # compute metrics
        self.D98 = self.compute_band_Dx(98)
        self.D95 = self.compute_band_Dx(95)
        self.D50 = self.compute_band_Dx(50)
        self.D5 = self.compute_band_Dx(5)
        self.D2 = self.compute_band_Dx(2)

    def compute_band_Dx(self, x):
        dose = self._dvh.dose

        index = np.searchsorted(-self.volume_low, -x)
        if (index > len(self.volume_low) - 2): index = len(self.volume_low) - 2
        volume = self.volume_low[index]
        volume2 = self.volume_low[index + 1]
        if (volume == volume2):
            low_Dx = dose[index]
        else:
            w2 = (volume - x) / (volume - volume2)
            w1 = (x - volume2) / (volume - volume2)
            low_Dx = w1 * dose[index] + w2 * dose[index + 1]
            if low_Dx < 0: low_Dx = 0

        index = np.searchsorted(-self.volume_high, -x)
        if (index > len(self.volume_high) - 2): index = len(self.volume_high) - 2
        volume = self.volume_high[index]
        volume2 = self.volume_high[index + 1]
        if (volume == volume2):
            high_Dx = dose[index]
        else:
            w2 = (volume - x) / (volume - volume2)
            w1 = (x - volume2) / (volume - volume2)
            high_Dx = w1 * dose[index] + w2 * dose[index + 1]
            if high_Dx < 0: high_Dx = 0

        return [low_Dx, high_Dx]
