import copy
import logging

import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QPushButton, QCheckBox, QDialog, \
    QLineEdit

from opentps.core.data.images import CTImage
from opentps.core.data.plan import ObjectivesList
from opentps.core.data.plan import PlanDesign, Robustness
from opentps.core.data import Patient
from opentps.core.io import mcsquareIO
from opentps.core.io.scannerReader import readScanner
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.processing.planOptimization.planOptimization import IMPTPlanOptimizer, BoundConstraintsOptimizer
from opentps.gui.panels.doseComputationPanel import DoseComputationPanel
from opentps.gui.panels.patientDataWidgets import PatientDataComboBox
from opentps.gui.panels.planOptimizationPanel.objectivesWindow import ObjectivesWindow
from opentps.gui.panels.planOptimizationPanel.optimizationSettings import OptiSettingsDialog

logger = logging.getLogger(__name__)

class mcsquareCalculationWindow(QDialog):
    def __init__(self, viewController, parent=None, contours=None, beamlets=True, robustOpti=False):
        super().__init__(parent)

        self._viewController = viewController
        self._contours = contours
        self._beamlets = beamlets
        self._robustOpti = robustOpti

        self._doseComputationPanel = DoseComputationPanel(viewController)

        self._doseComputationPanel._runButton.hide()
        self._doseComputationPanel._mcsquareConfigWidget.hide()

        if self._beamlets:
            self._doseComputationPanel._doseSpacingLabel.show()
            self._doseComputationPanel._numProtons.setValue(5e4)
            self._doseComputationPanel._numProtons.setDecimals(0)
            self._doseComputationPanel._cropBLBox.show()
            if not(self._doseComputationPanel._cropBLBox.isChecked()):
                self._contours = None

            self._beamletButton = QPushButton('Compute beamlets')
            self._beamletButton.clicked.connect(self._computeBeamlets)
            self._doseComputationPanel.layout.addWidget(self._beamletButton)
        else:
            self._optimizeButton = QPushButton('Beamlet-free optimize')
            self._optimizeButton.clicked.connect(self._optimizeBeamletFree)
            self._doseComputationPanel.layout.addWidget(self._optimizeButton)

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.layout.addWidget(self._doseComputationPanel)

    def setCT(self, ct):
        self._doseComputationPanel.selectedCT = ct

    def setPlan(self, plan):
        self._doseComputationPanel.selectedPlan = plan

    def _computeBeamlets(self):
        settings = DoseCalculationConfig()

        beamModel = mcsquareIO.readBDL(settings.bdlFile)
        calibration = readScanner(settings.scannerFolder)

        doseCalculator = MCsquareDoseCalculator()

        doseCalculator.beamModel = beamModel
        if self._doseComputationPanel._doseSpacingLabel.isChecked():
            self._doseComputationPanel.selectedPlan.planDesign.setScoringParameters(scoringSpacing=self._doseComputationPanel._doseSpacingSpin.value(), adapt_gridSize_to_new_spacing=True)
            # self._doseComputationPanel.selectedPlan.planDesign.scoringVoxelSpacing = self._doseComputationPanel._doseSpacingSpin.value()
        doseCalculator.nbPrimaries = self._doseComputationPanel._numProtons.value()
        doseCalculator.statUncertainty = self._doseComputationPanel._statUncertainty.value()
        doseCalculator.ctCalibration = calibration
        doseCalculator.overwriteOutsideROI = self._doseComputationPanel._selectedROI

        if self._robustOpti:
            nominal, scenarios = doseCalculator.computeRobustScenarioBeamlets(self._doseComputationPanel.selectedCT,
                                                   self._doseComputationPanel.selectedPlan, self._contours)
            self._doseComputationPanel.selectedPlan.planDesign.beamlets = nominal
            self._doseComputationPanel.selectedPlan.planDesign.robustness.scenarios = scenarios
            self._doseComputationPanel.selectedPlan.planDesign.robustness.numScenarios = len(scenarios)
        else:
            beamlets = doseCalculator.computeBeamlets(self._doseComputationPanel.selectedCT,
                                                   self._doseComputationPanel.selectedPlan, self._contours)
            self._doseComputationPanel.selectedPlan.planDesign.beamlets = beamlets
        self.accept()

    def _optimizeBeamletFree(self):
        settings = DoseCalculationConfig()

        beamModel = mcsquareIO.readBDL(settings.bdlFile)
        calibration = readScanner(settings.scannerFolder)

        doseCalculator = MCsquareDoseCalculator()
        doseCalculator.beamModel = beamModel
        doseCalculator.nbPrimaries = self._doseComputationPanel._numProtons.value()
        doseCalculator.ctCalibration = calibration

        doseImage = doseCalculator.optimizeBeamletFree(self._doseComputationPanel.selectedCT,
                                                       self._doseComputationPanel.selectedPlan,
                                                       self._contours)
        doseImage.patient = self._doseComputationPanel.selectedCT.patient
        self.accept()

class PlanOptiPanel(QWidget):
    _optiAlgos = ["Scipy-LBFGS (recommended)", "Scipy-BFGS", "In-house Gradient", "In-house LBFGS", "In-house BFGS", "FISTA",
                  "LP", "Beamlet-free MCsquare"]

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient: Patient = None
        self._optiConfig = {"method": "Scipy-LBFGS", "maxIter": 1000, "step": 0.02, "bounds": None}

        self._viewController = viewController

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._planStructureLabel = QLabel('Plan design:')
        self.layout.addWidget(self._planStructureLabel)
        self._planStructureComboBox = PatientDataComboBox(patientDataType=PlanDesign, patient=self._patient,
                                                          parent=self)
        self._planStructureComboBox.selectedDataEvent.connect(self._handlePlanStructure)
        self.layout.addWidget(self._planStructureComboBox)

        self._ctLabel = QLabel('CT:')
        self.layout.addWidget(self._ctLabel)
        self._ctComboBox = PatientDataComboBox(patientDataType=CTImage, patient=self._patient, parent=self)
        self.layout.addWidget(self._ctComboBox)

        self._objectivesWidget = ObjectivesWidget(self._viewController)
        self._objectivesWidget.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self._objectivesWidget)

        self.layout.addWidget(QLabel('Optimization algorithm:'))
        self._algoBox = QComboBox()
        self._algoBox.addItem(self._optiAlgos[0])
        self._algoBox.addItem(self._optiAlgos[1])
        self._algoBox.addItem(self._optiAlgos[2])
        self._algoBox.addItem(self._optiAlgos[3])
        self._algoBox.addItem(self._optiAlgos[4])
        self._algoBox.addItem(self._optiAlgos[5])
        self._algoBox.addItem(self._optiAlgos[6])
        self._algoBox.addItem(self._optiAlgos[7])
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

        self._planLabel = QLabel('plan name:')
        self.layout.addWidget(self._planLabel)
        self._planNameEdit = QLineEdit(self)
        self._planNameEdit.setText('New plan')
        self.layout.addWidget(self._planNameEdit)

        self._runButton = QPushButton('Optimize plan')
        self._runButton.clicked.connect(self._run)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

        self._handleAlgo()
        self._handlePlanStructure()

    @property
    def selectedCT(self):
        return self._ctComboBox.selectedData

    @property
    def selectedPlanStructure(self):
        return self._planStructureComboBox.selectedData

    def _handlePlanStructure(self, *args):
        self._objectivesWidget.planDesign = self.selectedPlanStructure

    def setCurrentPatient(self, patient: Patient):
        self._planStructureComboBox.setPatient(patient)
        self._ctComboBox.setPatient(patient)

        self._objectivesWidget.setPatient(patient)

    def _openConfig(self):
        dialog = OptiSettingsDialog(self._optiConfig)
        if dialog.exec(): dialog.optiParam
        logger.info('opti config = {}'.format(self._optiConfig))
        self._algoBox.setCurrentText(self._optiConfig['method'])

    def _run(self):
        settings = DoseCalculationConfig()
        ctCalibration = readScanner(settings.scannerFolder)

        self.selectedPlanStructure.ct = self.selectedCT
        self.selectedPlanStructure.calibration = ctCalibration

        self._setObjectives()

        # create list of contours
        objROINames = []
        contours = []
        for obj in self.selectedPlanStructure.objectives.fidObjList:
            # remove duplicate
            if obj.roiName not in objROINames:
                objROINames.append(obj.roiName)
                contours.append(obj.roi)

        self.selectedPlanStructure.defineTargetMaskAndPrescriptionFromObjList()

        if self._spotPlacementBox.isChecked():
            self._placeSpots()

        else:
            self._plan = copy.deepcopy(self._plan)
            self._plan.spotMUs = np.ones(self._plan.spotMUs.shape)
            self._plan.planDesign = self.selectedPlanStructure

        self._plan.name = self._planNameEdit.text()

        if self._beamletBox.isChecked() and self._beamletBox.isEnabled():
            self._computeBeamlets(contours)

        self._optimize(contours)

    def _setObjectives(self):
        objectiveList = ObjectivesList()
        for obj in self._objectivesWidget.objectives:
            objectiveList.append(obj)

        self.selectedPlanStructure.objectives = objectiveList
        for obj in self.selectedPlanStructure.objectives.fidObjList:
            if obj.robust:
                continue

    def _placeSpots(self):
        self._plan = self.selectedPlanStructure.buildPlan()  # Spot placement

    def _computeBeamlets(self, contours):
        robustOpti = self.selectedPlanStructure.robustness.selectionStrategy != Robustness.Strategies.DISABLED

        self._mcsquareWindow = mcsquareCalculationWindow(self._viewController, self, contours, beamlets=True, robustOpti=robustOpti)
        self._mcsquareWindow.setWindowTitle('Beamlet-based configuration')
        self._mcsquareWindow.setCT(self.selectedPlanStructure.ct)
        self._plan.patient = self.selectedPlanStructure.ct.patient
        self._mcsquareWindow.setPlan(self._plan)
        self._mcsquareWindow.exec()

    def _handleAlgo(self):
        if self._selectedAlgo == "Beamlet-free MCsquare":
            self._beamletBox.setEnabled(False)
            self._configButton.setEnabled(False)
        else:
            self._beamletBox.setEnabled(True)
            if self._selectedAlgo in ["Scipy-LBFGS (recommended)", "Scipy-BFGS", "In-house Gradient", "In-house LBFGS", "In-house BFGS", "FISTA"]:
                self._configButton.setEnabled(True)
                self._optiConfig['method'] = self._selectedAlgo
            else:
                self._configButton.setEnabled(False)

    @property
    def _selectedAlgo(self):
        return self._optiAlgos[self._algoBox.currentIndex()]

    def _optimize(self, contours):
        # Check if robust optimization compatible with solver:
        robustOpti = self.selectedPlanStructure.robustness.selectionStrategy != Robustness.Strategies.DISABLED
        if robustOpti and self._selectedAlgo in ["Beamlet-free MCsquare", "FISTA", "LP"]:
            raise NotImplementedError("Robust optimization is not supported for {} algorithm".format(self._selectedAlgo))

        if self._selectedAlgo == "Beamlet-free MCsquare":
            self._mcsquareWindow = mcsquareCalculationWindow(self._viewController, self, contours, beamlets=False)
            self._mcsquareWindow.setWindowTitle('Beamlet-free configuration')
            self._mcsquareWindow.setCT(self.selectedPlanStructure.ct)
            self._plan.patient = self.selectedPlanStructure.ct.patient
            self._mcsquareWindow.setPlan(self._plan)
            self._mcsquareWindow.exec()

        else:
            if self._selectedAlgo == "Scipy-BFGS":
                method = 'Scipy_BFGS'
            if self._selectedAlgo == "Scipy-LBFGS (recommended)":
                method = 'Scipy_L-BFGS-B'
            elif self._selectedAlgo == "In-house BFGS":
                method = 'BFGS'
            elif self._selectedAlgo == "In-house LBFGS":
                method = 'LBFGS'
            elif self._selectedAlgo == "In-house Gradient":
                method = 'Gradient'
            elif self._selectedAlgo == "FISTA":
                method = 'FISTA'
            elif self._selectedAlgo == "LP":
                method = 'LP'

            if self._optiConfig['bounds']:
                solver = BoundConstraintsOptimizer(method = method, plan = self._plan, bounds = self._optiConfig['bounds'], maxiter=self._optiConfig['maxIter'])
            else:
                solver = IMPTPlanOptimizer(method=method, plan=self._plan, maxiter=self._optiConfig['maxIter'])
            # Optimize treatment plan
            doseImage, _ = solver.optimize()
            doseImage.patient = self._mcsquareWindow._doseComputationPanel.selectedCT.patient


class ObjectivesWidget(QWidget):
    DEFAULT_OBJECTIVES_TEXT = 'No objective defined yet'

    def __init__(self, viewController):
        QWidget.__init__(self)

        self._planDesign = None

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

    @property
    def planDesign(self):
        return self._planDesign

    @planDesign.setter
    def planDesign(self, pd):
        self._planDesign = pd

        if not (self._planDesign is None):
            self._roiWindow.planDesign = self._planDesign

    def setPatient(self, p: Patient):
        self._roiWindow.patient = p

    def _showObjectives(self):
        objectives = self._roiWindow.getObjectiveTerms()

        if len(objectives) <= 0:
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
            objStr += ' Gy'

            if objective.robust:
                objStr += " (robust)\n"
            else: objStr += '\n'

        self._objectivesLabels.setText(objStr)

    def _openObjectivePanel(self):
        self._roiWindow.planDesign = self.planDesign
        self._roiWindow.show()
