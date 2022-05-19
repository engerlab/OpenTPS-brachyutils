from typing import Sequence

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QLineEdit, QPushButton, QTableWidget, \
    QTableWidgetItem

from Core.Data.Images.ctImage import CTImage
from Core.Data.patient import Patient
from Core.IO import mcsquareIO
from Core.IO.scannerReader import readScanner
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Extensions.FLASH.Core.Processing.CEMOptimization import cemObjectives
from programSettings import ProgramSettings


class PlanOptiPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._ctImages = []
        self._selectedCT = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._planLabel = QLabel('Label:')
        self.layout.addWidget(self._planLabel)

        self._ctLabel = QLabel('CT:')
        self.layout.addWidget(self._ctLabel)
        self._ctComboBox = QComboBox(self)
        self._ctComboBox.currentIndexChanged.connect(self._handleCTIndex)
        self.layout.addWidget(self._ctComboBox)

        self._roiTable = ROITable(self._viewController, parent=self)
        self.layout.addWidget(self._roiTable)

        self._primariesLabel = QLabel('Primaries:')
        self.layout.addWidget(self._primariesLabel)
        self._primariesEdit = QLineEdit(self)
        self._primariesEdit.setText(str(int(1e7)))
        self.layout.addWidget(self._primariesEdit)

        self._runButton = QPushButton('Run')
        self._runButton.clicked.connect(self._run)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    def _handleCTIndex(self, *args):
        self._selectedCT = self._ctImages[self._ctComboBox.currentIndex()]

    def setCurrentPatient(self, patient:Patient):
        if not (self._patient is None):
            self._patient.imageAddedSignal.disconnect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.disconnect(self._handleImageAddedOrRemoved)

        self._patient = patient
        self._roiTable.setCurrentPatient(self._patient)

        if self._patient is None:
            self._removeAllCTs()
        else:
            self._updateCTComboBox()

            self._patient.imageAddedSignal.connect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.connect(self._handleImageAddedOrRemoved)

    def _updateCTComboBox(self):
        self._removeAllCTs()

        self._ctImages = [ct for ct in self._patient.getPatientDataOfType(CTImage)]

        for ct in self._ctImages:
            self._addCT(ct)

        try:
            currentIndex = self._ctImages.index(self._selectedCT)
            self._ctComboBox.setCurrentIndex(currentIndex)
        except:
            self._ctComboBox.setCurrentIndex(0)
            if len(self._ctImages):
                self._selectedCT = self._ctImages[0]

    def _removeAllCTs(self):
        for ct in self._ctImages:
            self._removeCT(ct)

    def _removeAllROIs(self):
        for roi in self._rois:
            self._removeROI(roi)

    def _addCT(self, ct:CTImage):
        self._ctComboBox.addItem(ct.name, ct)
        ct.nameChangedSignal.connect(self._handleCTChanged)

    def _removeCT(self, ct:CTImage):
        if ct==self._selectedCT:
            self._selectedCT = None

        ct.nameChangedSignal.disconnect(self._handleCTChanged)
        self._ctComboBox.removeItem(self._ctComboBox.findData(ct))

    def _handleImageAddedOrRemoved(self, image):
        self._updateCTComboBox()

    def _handleCTChanged(self, ct):
        self._updateCTComboBox()

    def _run(self):
        settings = ProgramSettings()

        beamModel = mcsquareIO.readBDL(settings.bdlFile)
        calibration = readScanner(settings.scannerFolder)

        doseCalculator = MCsquareDoseCalculator()

        doseCalculator.beamModel = beamModel
        doseCalculator.nbPrimaries = int(self._primariesEdit.text())
        doseCalculator.ctCalibration = calibration
        doseCalculator.overwriteOutsideROI = self._selectedROI

        doseImage = doseCalculator.computeDose(self._selectedCT, self._selectedPlan)
        doseImage.patient = self._selectedCT.patient

class ROITable(QTableWidget):
    DMIN_THRESH = 0.
    DMAX_THRESH = 999.
    DEFAULT_WEIGHT = 1.

    def __init__(self, viewController, parent=None):
        super().__init__(100, 4, parent)

        self._rois = []

        self._viewController = viewController
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def setCurrentPatient(self, patient):
        self.reset()

        if not(patient is None):
            self._fillRoiTable(patient)

    def _fillRoiTable(self, patient:Patient):
        self._rois = []
        i = 0
        for rtStruct in patient.rtStructs:
            for contour in rtStruct.contours:
                newitem = QTableWidgetItem(contour.name)
                self.setItem(i, 0, newitem)
                self.setItem(i, 1, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
                self.setItem(i, 2, QTableWidgetItem(str(self.DMIN_THRESH)))
                self.setItem(i, 3, QTableWidgetItem(str(self.DMAX_THRESH)))

                self._rois.append(contour)

                i += 1

        for roiMask in patient.roiMasks:
            newitem = QTableWidgetItem(roiMask.name)
            self.setItem(i, 0, newitem)
            self.setItem(i, 1, QTableWidgetItem(str(self.DEFAULT_WEIGHT)))
            self.setItem(i, 2, QTableWidgetItem(str(self.DMIN_THRESH)))
            self.setItem(i, 3, QTableWidgetItem(str(self.DMAX_THRESH)))

            self._rois.append(roiMask)

            i += 1

        self.setHorizontalHeaderLabels(['ROI', 'Weight', 'Dmin', 'Dmax'])

    def getObjectiveTerms(self) -> Sequence[cemObjectives.CEMAbstractDoseFidelityTerm]:
        terms = []

        for i in range(len(self._rois)):
            weight = float(self.item(i, 1).text())
            # Dmin
            dmin = float(self.item(i, 2).text())
            if dmin > self.DMIN_THRESH:
                obj = cemObjectives.DoseMinObjective(self._rois[i], dmin)
                objective = workflows.Objective(objectiveTerm=obj, weight=weight)
                terms.append(objective)
            # Dmax
            dmax = float(self.item(i, 3).text())
            if dmax < self.DMAX_THRESH:
                obj = cemObjectives.DoseMaxObjective(self._rois[i], dmax)
                objective = workflows.Objective(objectiveTerm=obj, weight=weight)
                terms.append(objective)

        return terms

    def getROIs(self):
        rois = []

        for i in range(len(self._rois)):
            # Dmin
            dmin = float(self.item(i, 2).text())
            if dmin > self.DMIN_THRESH:
                rois.append(self._rois[i])
            # Dmax
            dmax = float(self.item(i, 3).text())
            if dmax < self.DMAX_THRESH:
                rois.append(self._rois[i])

        return rois
