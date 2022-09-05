
from typing import Sequence, Optional

from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

from Core.Data.Plan._objectivesList import FidObjective
from Core.Data._patient import Patient
from Core.event import Event

class ROITable(QTableWidget):
    DMIN_THRESH = 0.
    DMAX_THRESH = 999.
    DEFAULT_WEIGHT = 1.

    def __init__(self, viewController, parent=None):
        super().__init__(100, 5, parent)

        self.objectivesModifiedEvent = Event()

        self._patient:Optional[Patient] = None
        self._rois = []

        self._viewController = viewController

        self.cellChanged.connect(lambda *args: self.objectivesModifiedEvent.emit())

    def closeEvent(self, QCloseEvent):
        if not self._patient is None:
            self._patient.rtStructAddedSignal.disconnect(self.updateTable)
            self._patient.rtStructRemovedSignal.disconnect(self.updateTable)

        super().closeEvent(QCloseEvent)

    @property
    def patient(self) -> Optional[Patient]:
        return self._patient

    @patient.setter
    def patient(self, p:Optional[Patient]):
        if p==self._patient:
            return

        if not self._patient is None:
            self._patient.rtStructAddedSignal.disconnect(self.updateTable)
            self._patient.rtStructRemovedSignal.disconnect(self.updateTable)

        self._patient = p

        self._patient.rtStructAddedSignal.connect(self.updateTable)
        self._patient.rtStructRemovedSignal.connect(self.updateTable)

        self.updateTable()

    def updateTable(self, *args):
        self.reset()
        self._fillRoiTable()
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.objectivesModifiedEvent.emit()

    def _fillRoiTable(self):
        patient = self._viewController.currentPatient

        self._rois = []
        i = 0
        for rtStruct in patient.rtStructs:
            for contour in rtStruct.contours:
                newitem = QTableWidgetItem(contour.name)
                self.setItem(i, 0, newitem)
                self.setItem(i, 1, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(i, 2, QTableWidgetItem(str(self.DMIN_THRESH)))
                self.setItem(i, 3, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(i, 4, QTableWidgetItem(str(self.DMAX_THRESH)))

                self._rois.append(contour)

                i += 1

        for roiMask in patient.roiMasks:
            newitem = QTableWidgetItem(roiMask.name)
            self.setItem(i, 0, newitem)
            self.setItem(i, 1, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
            self.setItem(i, 2, QTableWidgetItem(str(self.DMIN_THRESH)))
            self.setItem(i, 3, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
            self.setItem(i, 4, QTableWidgetItem(str(self.DMAX_THRESH)))

            self._rois.append(roiMask)

            i += 1

        self.setHorizontalHeaderLabels(['ROI', 'W', 'Dmin', 'W', 'Dmax'])

    def getObjectiveTerms(self) -> Sequence[FidObjective]:
        terms = []

        for i, roi in enumerate(self._rois):
            # TODO How can this happen? It does happen when we load a new RTStruct for the same patient
            if self.item(i, 2) is None:
                return terms

            # Dmin
            dmin = float(self.item(i, 2).text())
            if dmin > self.DMIN_THRESH:
                obj = FidObjective(roi=roi)
                obj.metric = obj.Metrics.DMIN
                obj.weight = float(self.item(i, 1).text())
                obj.limitValue = dmin
                terms.append(obj)
            # Dmax
            dmax = float(self.item(i, 4).text())
            if dmax < self.DMAX_THRESH:
                obj = FidObjective(roi=roi)
                obj.metric = obj.Metrics.DMAX
                obj.weight = float(self.item(i, 3).text())
                obj.limitValue = dmax
                terms.append(obj)

        return terms

    def getROIs(self):
        rois = []

        for i in range(len(self._rois)):
            # Dmin
            dmin = float(self.item(i, 2).text())
            if dmin > self.DMIN_THRESH:
                rois.append(self._rois[i])
            # Dmax
            dmax = float(self.item(i, 4).text())
            if dmax < self.DMAX_THRESH:
                rois.append(self._rois[i])

        return rois
