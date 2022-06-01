from typing import Sequence, Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QLineEdit, QPushButton, QDoubleSpinBox, \
    QTableWidget, QTableWidgetItem, QMainWindow

from Core.Data.Images.ctImage import CTImage
from Core.Data.patient import Patient
from Core.event import Event

class PlanOptiPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._ctImages = []
        self._selectedCT = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._planLabel = QLabel('Plan name:')
        self.layout.addWidget(self._planLabel)
        self._planNameEdit = QLineEdit(self)
        self._planNameEdit.setText('New plan')
        self.layout.addWidget(self._planNameEdit)

        self._ctLabel = QLabel('CT:')
        self.layout.addWidget(self._ctLabel)
        self._ctComboBox = QComboBox(self)
        self._ctComboBox.currentIndexChanged.connect(self._handleCTIndex)
        self.layout.addWidget(self._ctComboBox)

        self._spacingLabel = QLabel('Spot spacing:')
        self.layout.addWidget(self._spacingLabel)
        self._spacingSpin = QDoubleSpinBox()
        self._spacingSpin.setGroupSeparatorShown(True)
        self._spacingSpin.setRange(0.1, 100.0)
        self._spacingSpin.setSingleStep(1.0)
        self._spacingSpin.setValue(5.0)
        self._spacingSpin.setSuffix(" mm")
        self.layout.addWidget(self._spacingSpin)

        self._layerLabel = QLabel('Layer spacing:')
        self.layout.addWidget(self._layerLabel)
        self._layerSpin = QDoubleSpinBox()
        self._layerSpin.setGroupSeparatorShown(True)
        self._layerSpin.setRange(0.1, 100.0)
        self._layerSpin.setSingleStep(1.0)
        self._layerSpin.setValue(2.0)
        self._layerSpin.setSuffix(" mm")
        self.layout.addWidget(self._layerSpin)

        self._marginLabel = QLabel('Target margin:')
        self.layout.addWidget(self._marginLabel)
        self._marginSpin = QDoubleSpinBox()
        self._marginSpin.setGroupSeparatorShown(True)
        self._marginSpin.setRange(0.1, 100.0)
        self._marginSpin.setSingleStep(1.0)
        self._marginSpin.setValue(5.0)
        self._marginSpin.setSuffix(" mm")
        self.layout.addWidget(self._marginSpin)

        self._objectivesWidget = ObjectivesWidget(self._viewController)
        self.layout.addWidget(self._objectivesWidget)

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

        if self._patient is None:
            self._removeAllCTs()
        else:
            self._updateCTComboBox()

            self._patient.imageAddedSignal.connect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.connect(self._handleImageAddedOrRemoved)

        self._objectivesWidget.setPatient(patient)

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
        pass

class ObjectivesWidget(QWidget):
    DEFAULT_OBJECTIVES_TEXT = 'No objective defined yet'

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._roiWindow = QMainWindow(self)
        self._roiWindow.hide()
        self._roitTable = ROITable(viewController, self._roiWindow)
        self._roiWindow.setCentralWidget(self._roitTable)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._objectivesLabels = QLabel(self.DEFAULT_OBJECTIVES_TEXT)
        self.layout.addWidget(self._objectivesLabels)

        self._objectiveButton = QPushButton('Open objectives panel')
        self._objectiveButton.clicked.connect(self._openObjectivePanel)
        self.layout.addWidget(self._objectiveButton)

        self._roitTable.objectivesModifiedEvent.connect(self._showObjectives)

    def setPatient(self, p:Patient):
        self._roitTable.patient = p

    def _showObjectives(self):
        # Modify this with conventional objectives!!!!!!!!!!!!!

        objStr = self.DEFAULT_OBJECTIVES_TEXT

        objectives = self._roitTable.getObjectiveTerms()

        if len(objectives)<=0:
            return

        objStr = ''
        for objective in objectives:
            objStr += str(objective.weight)
            objStr += " x "
            objStr += objective.objectiveTerm.roi.name

            if isinstance(objective.objectiveTerm, cemObjectives.DoseMinObjective):
                objStr += " < "
                objStr += str(objective.objectiveTerm.minDose)
            if isinstance(objective.objectiveTerm, cemObjectives.DoseMaxObjective):
                objStr += " > "
                objStr += str(objective.objectiveTerm.maxDose)

            objStr += ' Gy\n'

        self._objectivesLabels.setText(objStr)

    def _openObjectivePanel(self):
        self._roiWindow.show()

class ROITable(QTableWidget):
    DMIN_THRESH = 0.
    DMAX_THRESH = 999.
    DEFAULT_WEIGHT = 1.

    def __init__(self, viewController, parent=None):
        super().__init__(100, 4, parent)

        self.objectivesModifiedEvent = Event()

        self._patient:Optional[Patient] = None
        self._rois = []

        self._viewController = viewController

        self.cellChanged.connect(lambda *args: self.objectivesModifiedEvent.emit())

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
        patient = self._patient

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

    def getObjectiveTerms(self) -> Sequence:
        # Modify this with conventional objectives!!!!!!!!!!!!!
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
