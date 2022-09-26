import subprocess
import os
import platform

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QPushButton

from opentps.core.data.images import CTImage
from opentps.core.data.plan import ObjectivesList
from opentps.core.data.plan._planDesign import PlanDesign
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data._patient import Patient
from opentps.core.processing.planOptimization import optimizationWorkflows
from opentps.core.processing.planOptimization.planOptimizationConfig import PlanOptimizationConfig
from opentps.gui.panels.planOptimizationPanel.objectivesWindow import ObjectivesWindow


class PlanOptiPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._ctImages = []
        self._planStructures = []
        self._selectedCT = None
        self._selectedPlanStructure = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._planStructureLabel = QLabel('plan:')
        self.layout.addWidget(self._planStructureLabel)
        self._planStructureComboBox = QComboBox(self)
        self._planStructureComboBox.currentIndexChanged.connect(self._handlePlanStructureIndex)
        self.layout.addWidget(self._planStructureComboBox)

        self._ctLabel = QLabel('CT:')
        self.layout.addWidget(self._ctLabel)
        self._ctComboBox = QComboBox(self)
        self._ctComboBox.currentIndexChanged.connect(self._handleCTIndex)
        self.layout.addWidget(self._ctComboBox)

        self._objectivesWidget = ObjectivesWidget(self._viewController)
        self.layout.addWidget(self._objectivesWidget)

        self._configButton = QPushButton('Open configuration')
        self._configButton.clicked.connect(self._openConfig)
        self.layout.addWidget(self._configButton)

        from opentps.gui.programSettingEditor import MCsquareConfigEditor
        self._mcsquareConfigWidget = MCsquareConfigEditor(self)
        self.layout.addWidget(self._mcsquareConfigWidget)

        self._runButton = QPushButton('Run')
        self._runButton.clicked.connect(self._run)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    def _handlePlanStructureIndex(self):
        self._selectedPlanStructure = self._planStructures[self._planStructureComboBox.currentIndex()]

    def _handleCTIndex(self, *args):
        self._selectedCT = self._ctImages[self._ctComboBox.currentIndex()]

    def setCurrentPatient(self, patient:Patient):
        if not (self._patient is None):
            self._patient.imageAddedSignal.disconnect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.disconnect(self._handleImageAddedOrRemoved)
            self._patient.patientDataAddedSignal.disconnect(self._handlePlanStructureAddedOrRemoved)
            self._patient.patientDataAddedSignal.disconnect(self._handlePlanStructureAddedOrRemoved)

        self._patient = patient

        if self._patient is None:
            self._removeAllCTs()
            self._removeAllPlanStructures()
        else:
            self._updateCTComboBox()
            self._updatePlanStructureComboBox()

            self._patient.imageAddedSignal.connect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.connect(self._handleImageAddedOrRemoved)
            self._patient.patientDataAddedSignal.connect(self._handlePlanStructureAddedOrRemoved)
            self._patient.patientDataAddedSignal.connect(self._handlePlanStructureAddedOrRemoved)

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

    def _updatePlanStructureComboBox(self):
        self._removeAllPlanStructures()

        self._planStructures = [ps for ps in self._patient.getPatientDataOfType(PlanDesign)]

        for ps in self._planStructures:
            self._addPlanStructure(ps)

        try:
            currentIndex = self._planStructures.index(self._selectedPlanStructure)
            self._planStructureComboBox.setCurrentIndex(currentIndex)
        except:
            self._planStructureComboBox.setCurrentIndex(0)
            if len(self._planStructures):
                self._selectedPlanStructure = self._planStructures[0]

    def _removeAllPlanStructures(self):
        for ps in self._planStructures:
            self._removePlanStructure(ps)

    def _addPlanStructure(self, ps:PlanDesign):
        self._planStructureComboBox.addItem(ps.name, ps)
        ps.nameChangedSignal.connect(self._handlePlanStructureChanged)

    def _removePlanStructure(self, ps:PlanDesign):
        if ps==self._selectedPlanStructure:
            self._selectedPlanStructure = None

        ps.nameChangedSignal.disconnect(self._handlePlanStructureChanged)
        self._planStructureComboBox.removeItem(self._planStructureComboBox.findData(ps))

    def _handleImageAddedOrRemoved(self, image):
        self._updateCTComboBox()

    def _handleCTChanged(self, ct):
        self._updateCTComboBox()

    def _handlePlanStructureAddedOrRemoved(self, data):
        if isinstance(data, PlanDesign):
            self._updatePlanStructureComboBox()
    def _handlePlanStructureChanged(self, ct):
        self._updatePlanStructureComboBox()

    def _openConfig(self):
        if platform.system() == "Windows":
            os.system("start " + PlanOptimizationConfig().configFile)
        else:
            subprocess.run(['xdg-open', PlanOptimizationConfig().configFile], check=True)

    def _run(self):
        self._selectedPlanStructure.ct = self._selectedCT
        plan = RTPlan()
        plan.name = self._selectedPlanStructure.name
        plan.patient = self._selectedPlanStructure.patient

        objectiveList = ObjectivesList()
        for obj in self._objectivesWidget.objectives:
            objectiveList.append(obj)

        self._selectedPlanStructure.objectives = objectiveList

        optimizationWorkflows.optimizeIMPT(plan, self._selectedPlanStructure)

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

        self._objectiveButton = QPushButton('Open objectives panel')
        self._objectiveButton.clicked.connect(self._openObjectivePanel)
        self.layout.addWidget(self._objectiveButton)

        self._objectivesLabels = QLabel(self.DEFAULT_OBJECTIVES_TEXT)
        self.layout.addWidget(self._objectivesLabels)

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
            objStr += str(objective.limitValue)
            objStr += ' Gy\n'

        self._objectivesLabels.setText(objStr)

    def _openObjectivePanel(self):
        self._roiWindow.show()

