from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QLineEdit, QPushButton, QDoubleSpinBox, \
    QHBoxLayout, QCheckBox

from opentps.core.data.images import CTImage
from opentps.core.data._patient import Patient
from opentps.core.data._roiContour import ROIContour
from opentps.core.data._rtStruct import RTStruct
from opentps.core.data.plan import RTPlan
from opentps.core.io import mcsquareIO
from opentps.core.io.scannerReader import readScanner
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.gui.panels.patientDataWidgets import PatientDataComboBox


class DoseComputationPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._ctImages = []
        self._selectedCT = None
        self._rois = []
        self._selectedROI = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._ctLabel = QLabel('CT:')
        self.layout.addWidget(self._ctLabel)
        self._ctComboBox = PatientDataComboBox(patientDataType=CTImage, patient=self._patient, parent=self)
        self.layout.addWidget(self._ctComboBox)

        self._planLabel = QLabel('Plan:')
        self.layout.addWidget(self._planLabel)
        self._planComboBox = PatientDataComboBox(patientDataType=RTPlan, patient=self._patient, parent=self)
        self.layout.addWidget(self._planComboBox)

        self._roiLabel = QLabel('Overwrite outside this ROI:')
        self.layout.addWidget(self._roiLabel)
        self._roiComboBox = QComboBox(self)
        self._roiComboBox.currentIndexChanged.connect(self._handleROIIndex)
        self.layout.addWidget(self._roiComboBox)

        self.layout.addSpacing(15)
        self._doseSpacingLayout = QHBoxLayout()
        self.layout.addLayout(self._doseSpacingLayout)

        self._doseSpacingLabel = QCheckBox('Scoring spacing:')
        self._doseSpacingLabel.toggled.connect(self._setScoringSpacingVisible)
        self._doseSpacingLayout.addWidget(self._doseSpacingLabel)
        self._doseSpacingSpin = QDoubleSpinBox()
        self._doseSpacingSpin.setGroupSeparatorShown(True)
        self._doseSpacingSpin.setRange(0.1, 100.0)
        self._doseSpacingSpin.setSingleStep(1.0)
        self._doseSpacingSpin.setValue(2.0)
        self._doseSpacingSpin.setSuffix(" mm")
        self._doseSpacingLayout.addWidget(self._doseSpacingSpin)
        self._doseSpacingSpin.hide()
        self._doseSpacingLabel.hide()

        self.layout.addSpacing(15)
        self._cropBLBox = QCheckBox('Crop Beamlets on ROI')
        self._cropBLBox.setChecked(True)
        self.layout.addWidget(self._cropBLBox)
        self._cropBLBox.hide()

        self.layout.addSpacing(15)
        self.layout.addWidget(QLabel('<b>Simulation statistics:</b>'))
        self._numProtons = QDoubleSpinBox()
        self._numProtons.setGroupSeparatorShown(True)
        self._numProtons.setRange(0, 1e9)
        self._numProtons.setSingleStep(1e6)
        self._numProtons.setValue(1e7)
        self._numProtons.setDecimals(0)
        self._numProtons.setSuffix(" protons")
        self.layout.addWidget(self._numProtons)
        self._statUncertainty = QDoubleSpinBox()
        self._statUncertainty.setGroupSeparatorShown(True)
        self._statUncertainty.setRange(0.0, 100.0)
        self._statUncertainty.setSingleStep(0.1)
        self._statUncertainty.setValue(2.0)
        self._statUncertainty.setSuffix("% uncertainty")
        self.layout.addWidget(self._statUncertainty)
        self.layout.addSpacing(15)

        from opentps.gui.programSettingEditor import MCsquareConfigEditor
        self._mcsquareConfigWidget = MCsquareConfigEditor(self)
        self.layout.addWidget(self._mcsquareConfigWidget)

        self.layout.addSpacing(15)
        self._runButton = QPushButton('Compute dose')
        self._runButton.clicked.connect(self._computeDose)
        self.layout.addWidget(self._runButton)



        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    @property
    def selectedCT(self):
        return self._ctComboBox.selectedData

    @selectedCT.setter
    def selectedCT(self, ct):
        self._ctComboBox.selectedData = ct

    @property
    def selectedPlan(self):
        return self._planComboBox.selectedData

    @selectedPlan.setter
    def selectedPlan(self, plan):
        self._planComboBox.selectedData = plan

    def _handleROIIndex(self, *args):
        self._selectedROI = self._rois[self._roiComboBox.currentIndex()]

    def setCurrentPatient(self, patient:Patient):
        if not (self._patient is None):
            self._patient.rtStructAddedSignal.disconnect(self._handleROIAddedOrRemoved)
            self._patient.rtStructRemovedSignal.disconnect(self._handleROIAddedOrRemoved)

        self._patient = patient

        if self._patient is None:
            self._removeAllCTs()
        else:

            self._patient.rtStructAddedSignal.connect(self._handleROIAddedOrRemoved)
            self._patient.rtStructRemovedSignal.connect(self._handleROIAddedOrRemoved)

            self._planComboBox.setPatient(patient)
            self._ctComboBox.setPatient(patient)

    def _setScoringSpacingVisible(self):
        if self._doseSpacingLabel.isChecked():
            self._doseSpacingSpin.show()
        else:
            self._doseSpacingSpin.hide()

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

    def _removeAllROIs(self):
        for roi in self._rois:
            self._removeROI(roi)

    def _addROI(self, roi:ROIContour):
        self._roiComboBox.addItem(roi.name, roi)
        roi.nameChangedSignal.connect(self._handleROIChanged)

    def _removeROI(self, roi:ROIContour):
        if roi==self._selectedROI:
            self._selectedROI = None

        roi.nameChangedSignal.disconnect(self._handleROIChanged)
        self._roiComboBox.removeItem(self._roiComboBox.findData(roi))

    def _handleROIAddedOrRemoved(self, roi):
        self._updateROIComboBox()

    def _handleROIChanged(self, roi):
        self._updateROIComboBox()

    def _computeDose(self):
        settings = DoseCalculationConfig()

        beamModel = mcsquareIO.readBDL(settings.bdlFile)
        calibration = readScanner(settings.scannerFolder)

#        self.selectedPlan.scoringVoxelSpacing = 3 * [self._doseSpacingSpin.value()]

        doseCalculator = MCsquareDoseCalculator()

        doseCalculator.beamModel = beamModel
        # self.selectedPlan.scoringVoxelSpacing = self._doseSpacingSpin.value()
        doseCalculator.setScoringParameters(scoringSpacing=self._doseSpacingSpin.value(), adapt_gridSize_to_new_spacing=True)
        doseCalculator.nbPrimaries = self._numProtons.value()
        doseCalculator.statUncertainty = self._statUncertainty.value()
        doseCalculator.ctCalibration = calibration
        doseCalculator.overwriteOutsideROI = self._selectedROI
        doseImage = doseCalculator.computeDose(self.selectedCT, self.selectedPlan)
        doseImage.patient = self.selectedCT.patient

