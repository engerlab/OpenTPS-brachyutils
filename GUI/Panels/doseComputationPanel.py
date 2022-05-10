from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QLineEdit, QPushButton

from Core.Data.Images.ctImage import CTImage
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.patient import Patient
from Core.IO import mcsquareIO
from Core.IO.scannerReader import readScanner
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from programSettings import ProgramSettings


class DoseComputationPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._ctImages = []
        self._selectedCT = None
        self._plans = []
        self._selectedPlan = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._ctLabel = QLabel('CT:')
        self.layout.addWidget(self._ctLabel)
        self._ctComboBox = QComboBox(self)
        self._ctComboBox.currentIndexChanged.connect(self._handleCTIndex)
        self.layout.addWidget(self._ctComboBox)

        self._ctLabel = QLabel('Plan:')
        self.layout.addWidget(self._ctLabel)
        self._planComboBox = QComboBox(self)
        self._planComboBox.currentIndexChanged.connect(self._handlePlanIndex)
        self.layout.addWidget(self._planComboBox)

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

    def _handlePlanIndex(self, *args):
        self._selectedPlan = self._plans[self._planComboBox.currentIndex()]

    def setCurrentPatient(self, patient:Patient):
        if not (self._patient is None):
            self._patient.imageAddedSignal.disconnect(self._handleImageAddedOrRemoved)
            self._patient.planAddedSignal.disconnect(self._handlePlanAddedorRemoved)
            self._patient.imageRemovedSignal.disconnect(self._handleImageAddedOrRemoved)
            self._patient.planRemovedSignal.disconnect(self._handlePlanAddedorRemoved)

        self._patient = patient

        if self._patient is None:
            self._removeAllCTs()
        else:
            self._updateCTComboBox()
            self._updatePlanComboBox()
            self._patient.imageAddedSignal.connect(self._handleImageAddedOrRemoved)
            self._patient.planAddedSignal.connect(self._handlePlanAddedorRemoved)
            self._patient.imageRemovedSignal.connect(self._handleImageAddedOrRemoved)
            self._patient.planRemovedSignal.connect(self._handlePlanAddedorRemoved)

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

    def _updatePlanComboBox(self):
        self._removeAllPlans()

        self._plans = [plan for plan in self._patient.getPatientDataOfType(RTPlan)]

        for plan in self._plans:
            self._addPlan(plan)

        try:
            currentIndex = self._plans.index(self._selectedPlan)
            self._planComboBox.setCurrentIndex(currentIndex)
        except:
            self._planComboBox.setCurrentIndex(0)
            if len(self._plans):
                self._selectedPlan = self._plans[0]

    def _removeAllCTs(self):
        for ct in self._ctImages:
            self._removeCT(ct)

    def _removeAllPlans(self):
        for plan in self._plans:
            self._removePlan(plan)

    def _addCT(self, ct:CTImage):
        self._ctComboBox.addItem(ct.name, ct)
        ct.nameChangedSignal.connect(self._handleCTChanged)

    def _addPlan(self, plan:RTPlan):
        self._planComboBox.addItem(plan.name, plan)
        plan.nameChangedSignal.connect(self._handlePlanChanged)

    def _removeCT(self, ct:CTImage):
        if ct==self._selectedCT:
            self._selectedCT = None

        ct.nameChangedSignal.disconnect(self._handleCTChanged)
        self._ctComboBox.removeItem(self._ctComboBox.findData(ct))

    def _removePlan(self, plan:RTPlan):
        if plan==self._selectedPlan:
            self._selectedPlan = None

        plan.nameChangedSignal.disconnect(self._handlePlanChanged)
        self._planComboBox.removeItem(self._planComboBox.findData(plan))

    def _handleImageAddedOrRemoved(self, image):
        self._updateCTComboBox()

    def _handlePlanAddedorRemoved(self, plan):
        self._updatePlanComboBox()

    def _handleCTChanged(self, ct):
        self._updateCTComboBox()

    def _handlePlanChanged(self, plan):
        self._updatePlanComboBox()

    def _run(self):
        settings = ProgramSettings()

        beamModel = mcsquareIO.readBDL(settings.bdlFile)
        calibration = readScanner(settings.scannerFolder)

        doseCalculator = MCsquareDoseCalculator()

        doseCalculator.beamModel = beamModel
        doseCalculator.nbPrimaries = int(self._primariesEdit.text())
        doseCalculator.ctCalibration = calibration

        doseImage = doseCalculator.computeDose(self._selectedCT, self._selectedPlan)
        doseImage.patient = self._selectedCT.patient
