import copy
import os
import pickle
from typing import Sequence, Optional

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMainWindow, QAction, QFileDialog, QToolBar, QCheckBox

from opentps.core.data.images import ROIMask
from opentps.core.data.plan import PlanDesign, Robustness
from opentps.core.data.plan._objectivesList import FidObjective, ObjectivesList
from opentps.core.data import Patient
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

    @property
    def planDesign(self) -> PlanDesign:
        return self._roitTable.planDesign

    @planDesign.setter
    def planDesign(self, pd: PlanDesign):
        self._roitTable.planDesign = pd

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
    DMEAN_THRESH = 999.
    DEFAULT_WEIGHT = 1.

    def __init__(self, viewController, parent=None):
        super().__init__(0, 8, parent)

        self.objectivesModifiedEvent = Event()
        self.robustnessEnabledEvent = Event(bool)

        self.setHorizontalHeaderLabels(['ROI', 'Robust', 'Weight', 'Dmin (Gy)', 'Weight', 'Dmax (Gy)', 'Weight', 'Dmean (Gy)'])
        self._roiCol = 0
        self._robustCol = 1
        self._weightMinCol = 2
        self._dMinCol = 3
        self._weightMaxCol = 4
        self._dMaxCol = 5
        self._weightMeanCol = 6
        self._dMeanCol = 7

        self._planDesign = None
        self._patient:Optional[Patient] = None
        self._robustnessEnabled = True
        self._rois = []

        self._viewController = viewController

        self.cellChanged.connect(lambda *args: self.objectivesModifiedEvent.emit())

    def closeEvent(self, QCloseEvent):
        if not self._patient is None:
            self._patient.rtStructAddedSignal.disconnect(self.updateTable)
            self._patient.rtStructRemovedSignal.disconnect(self.updateTable)

        super().closeEvent(QCloseEvent)

    @property
    def planDesign(self) -> PlanDesign:
        return self._planDesign

    @planDesign.setter
    def planDesign(self, pd:PlanDesign):
        if self._planDesign is None:
            robustnessChanged = True
        else:
            robustnessChanged = self.robustnessEnabled != (self._planDesign.robustness.selectionStrategy != Robustness.Strategies.DISABLED)
        if self._planDesign==pd and (not robustnessChanged):
            return

        self.updateTable()
        self._planDesign = pd
        self.robustnessEnabled = self._planDesign.robustness.selectionStrategy != Robustness.Strategies.DISABLED
        self.applyTemplate(self._planDesign.objectives.fidObjList)

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

    @property
    def robustnessEnabled(self):
        return self._robustnessEnabled

    @robustnessEnabled.setter
    def robustnessEnabled(self, enabled: bool):
        if self._robustnessEnabled == enabled:
            return

        for i, roi in enumerate(self._rois):
            if not enabled:
                self.cellWidget(i, self._robustCol).setChecked(False)
            self.cellWidget(i, self._robustCol).setEnabled(enabled)

        self._robustnessEnabled = enabled
        self.robustnessEnabledEvent.emit(self._robustnessEnabled)

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

        rowCount = 0
        for rtStruct in patient.rtStructs:
            rowCount += len(rtStruct.contours)
        rowCount += len(patient.roiMasks)

        self.setRowCount(rowCount)

        self._rois = []
        i = 0
        for rtStruct in patient.rtStructs:
            for contour in rtStruct.contours:
                self.setItem(i, self._roiCol, QTableWidgetItem(contour.name))
                robustCheckBox = QCheckBox(self)
                robustCheckBox.setEnabled(self._robustnessEnabled)
                self.setCellWidget(i, self._robustCol, robustCheckBox)
                self.setItem(i, self._weightMinCol, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(i, self._dMinCol, QTableWidgetItem(str(self.DMIN_THRESH)))
                self.setItem(i, self._weightMaxCol, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(i, self._dMaxCol, QTableWidgetItem(str(self.DMAX_THRESH)))
                self.setItem(i, self._weightMeanCol, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(i, self._dMeanCol, QTableWidgetItem(str(self.DMEAN_THRESH)))

                self._rois.append(contour)

                i += 1

        for roiMask in patient.roiMasks:
            self.setItem(i, self._roiCol, QTableWidgetItem(roiMask.name))
            robustCheckBox = QCheckBox(self)
            robustCheckBox.setEnabled(self._robustnessEnabled)
            self.setCellWidget(i, self._robustCol, robustCheckBox)
            self.setItem(i, self._weightMinCol, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
            self.setItem(i, self._dMinCol, QTableWidgetItem(str(self.DMIN_THRESH)))
            self.setItem(i, self._weightMaxCol, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
            self.setItem(i, self._dMaxCol, QTableWidgetItem(str(self.DMAX_THRESH)))
            self.setItem(i, self._weightMeanCol, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
            self.setItem(i, self._dMeanCol, QTableWidgetItem(str(self.DMEAN_THRESH)))

            self._rois.append(roiMask)

            i += 1

    def applyTemplate(self, template:Sequence[FidObjective]):
        roiNames = [roi.name for roi in self._rois]

        for obj in template:
            roiInd = roiNames.index(obj.roi.name)

            if obj.roi.name in roiNames:
                if obj.metric == FidObjective.Metrics.DMIN:
                    self.item(roiInd, self._weightMinCol).setText(str(obj.weight))
                    self.item(roiInd, self._dMinCol).setText(str(obj.limitValue))
                elif obj.metric == FidObjective.Metrics.DMAX:
                    self.item(roiInd, self._weightMaxCol).setText(str(obj.weight))
                    self.item(roiInd, self._dMaxCol).setText(str(obj.limitValue))
                elif obj.metric == FidObjective.Metrics.DMEAN:
                    self.item(roiInd, self._weightMeanCol).setText(str(obj.weight))
                    self.item(roiInd, self._dMeanCol).setText(str(obj.limitValue))
                else:
                    pass
                    #TODO: metrics not supported
            else:
                self.setItem(roiInd, self._weightMinCol, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(roiInd, self._dMinCol, QTableWidgetItem(str(self.DMIN_THRESH)))
                self.setItem(roiInd, self._weightMaxCol, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(roiInd, self._dMaxCol, QTableWidgetItem(str(self.DMAX_THRESH)))
                self.setItem(roiInd, self._weightMeanCol, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(roiInd, self._dMeanCol, QTableWidgetItem(str(self.DMEAN_THRESH)))

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
            if self.item(i, self._dMinCol) is None:
                return terms

            robust = self.cellWidget(i, self._robustCol).isChecked()

            # Dmin
            dmin = float(self.item(i, self._dMinCol).text())
            if dmin > self.DMIN_THRESH:
                obj = FidObjective(roi=roi)
                obj.metric = obj.Metrics.DMIN
                obj.weight = float(self.item(i, self._weightMinCol).text())
                obj.limitValue = dmin
                obj.robust = robust
                terms.append(obj)
            # Dmax
            dmax = float(self.item(i, self._dMaxCol).text())
            if dmax < self.DMAX_THRESH:
                obj = FidObjective(roi=roi)
                obj.metric = obj.Metrics.DMAX
                obj.weight = float(self.item(i, self._weightMaxCol).text())
                obj.limitValue = dmax
                obj.robust = robust
                terms.append(obj)
            # Dmean
            dmean = float(self.item(i, self._dMeanCol).text())
            if dmean < self.DMEAN_THRESH:
                obj = FidObjective(roi=roi)
                obj.metric = obj.Metrics.DMEAN
                obj.weight = float(self.item(i, self._weightMeanCol).text())
                obj.limitValue = dmean
                obj.robust = robust
                terms.append(obj)

        return terms

    def getROIs(self):
        rois = []

        for i in range(len(self._rois)):
            # Dmin
            dmin = float(self.item(i, self._dMinCol).text())
            if dmin > self.DMIN_THRESH:
                rois.append(self._rois[i])
            # Dmax
            dmax = float(self.item(i, self._dMaxCol).text())
            if dmax < self.DMAX_THRESH:
                rois.append(self._rois[i])
            # Dmean
            dmean = float(self.item(i, self._dMeanCol).text())
            if dmean < self.DMEAN_THRESH:
                rois.append(self._rois[i])

        return rois

    def _setObjectives(self):
        objectiveList = ObjectivesList()
        for obj in self._objectivesWidget.objectives:
            objectiveList.append(obj)

        self._planDesign.objectives = objectiveList
