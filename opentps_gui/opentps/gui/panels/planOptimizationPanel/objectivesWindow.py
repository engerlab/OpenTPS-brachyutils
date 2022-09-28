import copy
import os
import pickle
from typing import Sequence, Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMainWindow, QAction, QFileDialog, QToolBar

from opentps.core.data.images import ROIMask
from opentps.core.data.plan._objectivesList import FidObjective
from opentps.core.data._patient import Patient
from opentps.core import Event

import opentps.gui.res.icons as IconModule


class ObjectivesWindow(QMainWindow):
    def __init__(self, viewController, parent=None):

        super().__init__(parent)

        self.objectivesModifiedEvent = Event()

        self._viewController = viewController

        self._roitTable = ROITable(self._viewController, self)
        self._roitTable.objectivesModifiedEvent.connect(self.objectivesModifiedEvent.emit)
        self.setCentralWidget(self._roitTable)

        self._menuBar = QToolBar(self)
        self.addToolBar(self._menuBar)

        iconPath = IconModule.__path__[0] + os.path.sep

        self._openAction = QAction(QIcon(iconPath + 'folder-open.png'), "&Open template file", self)
        self._openAction.triggered.connect(self._handleOpen)
        self._menuBar.addAction(self._openAction)

        self._saveAction = QAction(QIcon(iconPath + 'disk.png'), "&Save template", self)
        self._saveAction.triggered.connect(self._handleSave)
        self._menuBar.addAction(self._saveAction)

    @property
    def patient(self):
        return self._roitTable.patient

    @patient.setter
    def patient(self, p:Patient):
        self._roitTable.patient = p

    def getObjectiveTerms(self) -> Sequence[FidObjective]:
        return self._roitTable.getObjectiveTerms()

    def _handleOpen(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Open file','c:\\', "Objective template")
        template = self._loadTemplate(fname)
        self._roitTable.applyTemplate(template)

    def _handleSave(self):
        fname, _ = QFileDialog.getSaveFileName(self, 'Save file','c:\\', "Objective template")
        self._saveTemplate(self._roitTable.getTemplate(), fname)

    def _saveTemplate(self, objectives:Sequence[FidObjective], filePath:str):
        with open(filePath, 'wb') as f:
            pickle.dump(objectives, f)

    def _loadTemplate(self, filePath:str) -> Sequence[FidObjective]:
        with open(filePath, 'rb') as f:
            res = pickle.load(f)

        return res


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

        if not self._patient is None:
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
        if patient is None:
            return

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

    def applyTemplate(self, template:Sequence[FidObjective]):
        roiNames = [roi.name for roi in self._rois]

        for obj in template:
            roiInd = roiNames.index(obj.roi.name)

            if obj.roi.name in roiNames:
                if obj.metric == FidObjective.Metrics.DMIN:
                    self.item(roiInd, 1).setText(str(obj.weight))
                    self.item(roiInd, 2).setText(str(obj.limitValue))
                elif obj.metric == FidObjective.Metrics.DMAX:
                    self.item(roiInd, 3).setText(str(obj.weight))
                    self.item(roiInd, 4).setText(str(obj.limitValue))
                else:
                    pass
                    #TODO: metrics not supported
            else:
                self.item(roiInd, 1).setText(str(1))
                self.item(roiInd, 2).setText(str(self.DMIN_THRESH))
                self.item(roiInd, 3).setText(str(1))
                self.item(roiInd, 4).setText(str(self.DMAX_THRESH))

    def getTemplate(self) -> Sequence[FidObjective]:
        objctivesToSave = []
        for objective in self.getObjectiveTerms():
            roi = objective.roi
            objective.roi = None
            objectiveCopy = copy.deepcopy(objective)
            objectiveCopy.roi = ROIMask(name=roi.name)
            objective.roi = roi
            objctivesToSave.append(objectiveCopy)

        return objctivesToSave

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
