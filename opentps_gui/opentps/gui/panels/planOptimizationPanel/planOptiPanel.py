import subprocess
import os
import platform

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QPushButton, QMainWindow, QCheckBox, QDialog

from opentps.core.data.images import CTImage
from opentps.core.data.plan import ObjectivesList
from opentps.core.data.plan._planDesign import PlanDesign
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data._patient import Patient
from opentps.core.io.scannerReader import readScanner
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.planOptimization import optimizationWorkflows
from opentps.core.processing.planOptimization.planOptimizationConfig import PlanOptimizationConfig
from opentps.gui.panels.doseComputationPanel import DoseComputationPanel
from opentps.gui.panels.patientDataWidgets import PatientDataComboBox
from opentps.gui.panels.planOptimizationPanel.objectivesWindow import ObjectivesWindow


class BeamletCalculationWindow(QDialog):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController

        self._doseComputationPanel = DoseComputationPanel(viewController)

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.layout.addWidget(self._doseComputationPanel)

    def setCT(self, ct):
        self._doseComputationPanel.selectedCT = ct

    def setPlan(self, plan):
        self._doseComputationPanel.selectedPlan = plan


class PlanOptiPanel(QWidget):
    _optiAlgos = ["Beamlet-free MCsquare", "Beamlet-based BFGS", "Beamlet-based L-BFGS", "Beamlet-based Scipy-lBFGS"]

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._planStructureLabel = QLabel('Plan design:')
        self.layout.addWidget(self._planStructureLabel)
        self._planStructureComboBox = PatientDataComboBox(patientDataType=PlanDesign, patient=self._patient, parent=self)
        self.layout.addWidget(self._planStructureComboBox)

        self._ctLabel = QLabel('CT:')
        self.layout.addWidget(self._ctLabel)
        self._ctComboBox = PatientDataComboBox(patientDataType=CTImage, patient=self._patient, parent=self)
        self.layout.addWidget(self._ctComboBox)

        from opentps.gui.programSettingEditor import MCsquareConfigEditor
        self._mcsquareConfigWidget = MCsquareConfigEditor(self)
        self._mcsquareConfigWidget.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self._mcsquareConfigWidget)

        self._objectivesWidget = ObjectivesWidget(self._viewController)
        self._objectivesWidget.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self._objectivesWidget)

        self.layout.addWidget(QLabel('Optimization algorithm:'))
        self._algoBox = QComboBox()
        self._algoBox.addItem(self._optiAlgos[0])
        self._algoBox.addItem(self._optiAlgos[1])
        self._algoBox.addItem(self._optiAlgos[2])
        self._algoBox.addItem(self._optiAlgos[3])
        self._algoBox.currentIndexChanged.connect(self._handleAlgo)
        self.layout.addWidget(self._algoBox)

        self._configButton = QPushButton('Advanced configuration')
        self._configButton.clicked.connect(self._openConfig)
        self.layout.addWidget(self._configButton)

        self._spotPlacementBox = QCheckBox('Place spots')
        self._spotPlacementBox.setChecked(True)
        self._beamletBox = QCheckBox('Compute beamlets')
        self._beamletBox.setChecked(True)
        self.layout.addWidget(self._spotPlacementBox)
        self.layout.addWidget(self._beamletBox)

        self._runButton = QPushButton('Optimize plan')
        self._runButton.clicked.connect(self._run)
        self.layout.addWidget(self._runButton)

        self._beamletWindow = BeamletCalculationWindow(viewController, self)
        self._beamletWindow.hide()

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

        self._handleAlgo()

    @property
    def selectedCT(self):
        return self._ctComboBox.selectedData

    @property
    def selectedPlanStructure(self):
        return self._planStructureComboBox.selectedData

    def setCurrentPatient(self, patient:Patient):
        self._planStructureComboBox.setPatient(patient)
        self._ctComboBox.setPatient(patient)

        self._objectivesWidget.setPatient(patient)

    def _openConfig(self):
        if platform.system() == "Windows":
            os.system("start " + PlanOptimizationConfig().configFile)
        else:
            subprocess.run(['xdg-open', PlanOptimizationConfig().configFile], check=True)

    def _run(self):
        settings = DoseCalculationConfig()
        ctCalibration = readScanner(settings.scannerFolder)

        self.selectedPlanStructure.ct = self.selectedCT
        self.selectedPlanStructure.calibration = ctCalibration

        self._setObjectives()

        if self._spotPlacementBox.isChecked():
            self._placeSpots()

        if self._beamletBox.isChecked() and self._beamletBox.isEnabled():
            self._computeBeamlets()

        self._optimize()

    def _setObjectives(self):
        objectiveList = ObjectivesList()
        for obj in self._objectivesWidget.objectives:
            objectiveList.append(obj)

        self.selectedPlanStructure.objectives = objectiveList

    def _placeSpots(self):
        self.selectedPlanStructure.defineTargetMaskAndPrescription()
        self._plan = self.selectedPlanStructure.buildPlan()  # Spot placement

    def _handleAlgo(self):
        if self._selectedAlgo == "Beamlet-free MCsquare":
            self._beamletBox.setEnabled(False)
        else:
            self._beamletBox.setEnabled(True)
    @property
    def _selectedAlgo(self):
        return self._optiAlgos[self._algoBox.currentIndex()]

    def _computeBeamlets(self):
        self._beamletWindow.setWindowTitle('Compute beamlets')
        self._beamletWindow.setCT(self.selectedPlanStructure.ct)
        self._plan.patient = self.selectedPlanStructure.ct.patient
        self._beamletWindow.setPlan(self._plan)
        self._beamletWindow.exec()

        self.selectedPlanStructure.scoringVoxelSpacing = self.selectedPlanStructure.beamlets.doseSpacing

    def _optimize(self):
        plan = RTPlan()
        plan.name = self.selectedPlanStructure.name
        plan.patient = self.selectedPlanStructure.patient

        optimizationWorkflows.optimizeIMPT(plan, self.selectedPlanStructure)


class ObjectivesWidget(QWidget):
    DEFAULT_OBJECTIVES_TEXT = 'No objective defined yet'

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._roiWindow = ObjectivesWindow(viewController, self)
        self._roiWindow.setMinimumWidth(400)
        self._roiWindow.setMinimumHeight(400)
        self._roiWindow.hide()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.setContentsMargins(0, 0, 0, 0)

        self._objectivesLabel = QLabel("Objectives:")
        self.layout.addWidget(self._objectivesLabel)

        self._objectivesLabels = QLabel(self.DEFAULT_OBJECTIVES_TEXT)
        self.layout.addWidget(self._objectivesLabels)

        self._objectiveButton = QPushButton('Open objectives panel')
        self._objectiveButton.clicked.connect(self._openObjectivePanel)
        self.layout.addWidget(self._objectiveButton)

        self._roiWindow.objectivesModifiedEvent.connect(self._showObjectives)

    def closeEvent(self, QCloseEvent):
        self._roitTable.objectivesModifiedEvent.disconnect(self._showObjectives)
        super().closeEvent(QCloseEvent)

    @property
    def objectives(self):
        return self._roiWindow.getObjectiveTerms()

    def setPatient(self, p:Patient):
        self._roiWindow.patient = p

    def _showObjectives(self):
        objectives = self._roiWindow.getObjectiveTerms()

        if len(objectives)<=0:
            self._objectivesLabels.setText(self.DEFAULT_OBJECTIVES_TEXT)
            return

        objStr = ''
        for objective in objectives:
            objStr += str(objective.weight)
            objStr += " x "
            objStr += objective.roiName

            if objective.metric == objective.Metrics.DMIN:
                objStr += ">"
            if objective.metric == objective.Metrics.DMAX:
                objStr += "<"
            elif objective.metric == objective.Metrics.DMEAN:
                objStr += "="
            objStr += str(objective.limitValue)
            objStr += ' Gy\n'

        self._objectivesLabels.setText(objStr)

    def _openObjectivePanel(self):
        self._roiWindow.show()

