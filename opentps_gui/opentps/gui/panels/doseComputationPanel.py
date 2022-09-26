from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QLineEdit, QPushButton

from opentps.core.data.images import CTImage
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data._patient import Patient
from opentps.core.data._roiContour import ROIContour
from opentps.core.data._rtStruct import RTStruct
from opentps.core.io import mcsquareIO
from opentps.core.io.scannerReader import readScanner
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator


class DoseComputationPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._ctImages = []
        self._selectedCT = None
        self._plans = []
        self._selectedPlan = None
        self._rois = []
        self._selectedROI = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._ctLabel = QLabel('CT:')
        self.layout.addWidget(self._ctLabel)
        self._ctComboBox = QComboBox(self)
        self._ctComboBox.currentIndexChanged.connect(self._handleCTIndex)
        self.layout.addWidget(self._ctComboBox)

        self._planLabel = QLabel('plan:')
        self.layout.addWidget(self._planLabel)
        self._planComboBox = QComboBox(self)
        self._planComboBox.currentIndexChanged.connect(self._handlePlanIndex)
        self.layout.addWidget(self._planComboBox)

        self._roiLabel = QLabel('Overwrite outside this ROI:')
        self.layout.addWidget(self._roiLabel)
        self._roiComboBox = QComboBox(self)
        self._roiComboBox.currentIndexChanged.connect(self._handleROIIndex)
        self.layout.addWidget(self._roiComboBox)

        self._primariesLabel = QLabel('Primaries:')
        self.layout.addWidget(self._primariesLabel)
        self._primariesEdit = QLineEdit(self)
        self._primariesEdit.setText(str(int(1e7)))
        self.layout.addWidget(self._primariesEdit)

        from opentps.gui.programSettingEditor import MCsquareConfigEditor
        self._mcsquareConfigWidget = MCsquareConfigEditor(self)
        self.layout.addWidget(self._mcsquareConfigWidget)

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

    def _handleROIIndex(self, *args):
        self._selectedROI = self._rois[self._roiComboBox.currentIndex()]

    def setCurrentPatient(self, patient:Patient):
        if not (self._patient is None):
            self._patient.imageAddedSignal.disconnect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.disconnect(self._handleImageAddedOrRemoved)

            self._patient.planAddedSignal.disconnect(self._handlePlanAddedOrRemoved)
            self._patient.planRemovedSignal.disconnect(self._handlePlanAddedOrRemoved)

            self._patient.rtStructAddedSignal.disconnect(self._handleROIAddedOrRemoved)
            self._patient.rtStructRemovedSignal.disconnect(self._handleROIAddedOrRemoved)

        self._patient = patient

        if self._patient is None:
            self._removeAllCTs()
        else:
            self._patient.imageAddedSignal.connect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.connect(self._handleImageAddedOrRemoved)

            self._patient.planAddedSignal.connect(self._handlePlanAddedOrRemoved)
            self._patient.planRemovedSignal.connect(self._handlePlanAddedOrRemoved)

            self._patient.rtStructAddedSignal.connect(self._handleROIAddedOrRemoved)
            self._patient.rtStructRemovedSignal.connect(self._handleROIAddedOrRemoved)

            self._updateCTComboBox()
            self._updatePlanComboBox()

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

    def _updateROIComboBox(self):
        self._removeAllROIs()

        rtstructs = self._patient.getPatientDataOfType(RTStruct)

        self._rois = []
        for struct in rtstructs:
            for roi in struct:
                self._rois.append(roi)

        for roi in self._rois:
            self._addROI(roi)

        try:
            currentIndex = self._rois.index(self._selectedROI)
            self._roiComboBox.setCurrentIndex(currentIndex)
        except:
            self._roiComboBox.setCurrentIndex(0)
            if len(self._rois):
                self._selectedROI = self._rois[0]

    def _removeAllCTs(self):
        for ct in self._ctImages:
            self._removeCT(ct)

    def _removeAllPlans(self):
        for plan in self._plans:
            self._removePlan(plan)

    def _removeAllROIs(self):
        for roi in self._rois:
            self._removeROI(roi)

    def _addCT(self, ct:CTImage):
        self._ctComboBox.addItem(ct.name, ct)
        ct.nameChangedSignal.connect(self._handleCTChanged)

    def _addPlan(self, plan:RTPlan):
        self._planComboBox.addItem(plan.name, plan)
        plan.nameChangedSignal.connect(self._handlePlanChanged)

    def _addROI(self, roi:ROIContour):
        self._roiComboBox.addItem(roi.name, roi)
        roi.nameChangedSignal.connect(self._handleROIChanged)

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

    def _removeROI(self, roi:ROIContour):
        if roi==self._selectedROI:
            self._selectedROI = None

        roi.nameChangedSignal.disconnect(self._handleROIChanged)
        self._roiComboBox.removeItem(self._roiComboBox.findData(roi))

    def _handleImageAddedOrRemoved(self, image):
        self._updateCTComboBox()

    def _handlePlanAddedOrRemoved(self, plan):
        self._updatePlanComboBox()

    def _handleROIAddedOrRemoved(self, roi):
        self._updateROIComboBox()

    def _handleCTChanged(self, ct):
        self._updateCTComboBox()

    def _handlePlanChanged(self, plan):
        self._updatePlanComboBox()

    def _handleROIChanged(self, roi):
        self._updateROIComboBox()

    def _run(self):
        settings = DoseCalculationConfig()

        beamModel = mcsquareIO.readBDL(settings.bdlFile)
        calibration = readScanner(settings.scannerFolder)

        doseCalculator = MCsquareDoseCalculator()

        doseCalculator.beamModel = beamModel
        doseCalculator.nbPrimaries = int(self._primariesEdit.text())
        doseCalculator.ctCalibration = calibration
        doseCalculator.overwriteOutsideROI = self._selectedROI

        doseImage = doseCalculator.computeDose(self._selectedCT, self._selectedPlan)
        doseImage.patient = self._selectedCT.patient
