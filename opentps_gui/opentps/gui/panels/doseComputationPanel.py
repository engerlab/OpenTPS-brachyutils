import logging
logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QLineEdit, QPushButton, QDoubleSpinBox, \
    QHBoxLayout, QCheckBox, QSpinBox
from PyQt5.QtCore import Qt
from opentps.core.data.images import CTImage
from opentps.core.data._patient import Patient
from opentps.core.data._roiContour import ROIContour
from opentps.core.data._rtStruct import RTStruct
from opentps.core.data.plan import RTPlan
from opentps.core.io import mcsquareIO
from opentps.core.io.scannerReader import readScanner
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.photons.cccDoseCalculator import CCCDoseCalculator
from opentps.core.processing.doseCalculation.protons.mcsquareDoseCalculator import MCsquareDoseCalculator
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
        self._radiationType = "PROTON" # default

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._radiationLabel = QLabel(self)
        self._radiationLabel.setFixedSize(100, 30)  
        self._radiationLabel.setAlignment(Qt.AlignCenter)  
        self.layout.addWidget(self._radiationLabel)

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
        self._cropBLBox = QCheckBox('Crop beamlets on ROI')
        self._cropBLBox.setChecked(True)
        self.layout.addWidget(self._cropBLBox)
        self._cropBLBox.hide()

        self.layout.addSpacing(15)
        self._simuProtonLabel = QLabel('<b>Simulation statistics:</b>')
        self.layout.addWidget(self._simuProtonLabel)
        self._numProtons = QSpinBox()
        self._numProtons.setGroupSeparatorShown(True)
        self._numProtons.setRange(0, int(1e9))
        self._numProtons.setSingleStep(int(1e6))
        self._numProtons.setValue(int(1e7))
        self._numProtons.setSuffix(" protons")
        self._simuProtonLabel.hide()
        self._numProtons.hide()

        self._statUncertainty = QDoubleSpinBox()
        self._statUncertainty.setGroupSeparatorShown(True)
        self._statUncertainty.setRange(0.0, 100.0)
        self._statUncertainty.setSingleStep(0.1)
        self._statUncertainty.setValue(2.0)
        self._statUncertainty.setSuffix("% uncertainty")
        self._statUncertainty.hide()
        self.layout.addWidget(self._numProtons)
        self.layout.addWidget(self._statUncertainty)
        self.layout.addSpacing(15)

        self._simuPhotonLabel = QLabel('<b>Simulation parameters:</b>')
        self.layout.addWidget(self._simuPhotonLabel)
        self._batchSize = QSpinBox()
        self._batchSize.setGroupSeparatorShown(True)
        self._batchSize.setRange(0, int(1e9))
        self._batchSize.setSingleStep(10)
        self._batchSize.setValue(30)
        self._batchSize.setSuffix(" (batch size)")
        self.layout.addWidget(self._batchSize)
        self._simuPhotonLabel.hide()
        self._batchSize.hide()


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
        self._planComboBox.selectedDataEvent.connect(self.updateUIBasedOnRadiationType)
    

    def updateUIBasedOnRadiationType(self,  selectedPlan):
        if selectedPlan is not None:
            if selectedPlan.modality=="RT Plan IOD" and selectedPlan.radiationType.upper()=="PHOTON":
                    self._radiationType = "PHOTON"
                    self._numProtons.hide()
                    self._statUncertainty.hide()
                    self._simuProtonLabel.hide()
                    self._batchSize.show()
                    self._simuPhotonLabel.show()
                    self._mcsquareConfigWidget._txt2.hide()
                    self._mcsquareConfigWidget._bdlField.hide()
                    self._radiationLabel.setText("PHOTON")
                    self._radiationLabel.setStyleSheet("background-color: yellow; color: black;")
            elif selectedPlan.modality=="RT Ion Plan IOD" and selectedPlan.radiationType.upper()=="PROTON":
                self._radiationType = "PROTON"
                self._numProtons.show()
                self._statUncertainty.show()
                self._simuProtonLabel.show()
                self._batchSize.hide()
                self._simuPhotonLabel.hide()
                self._mcsquareConfigWidget._txt2.show()
                self._mcsquareConfigWidget._bdlField.show()
                self._radiationLabel.setText("PROTON")
                self._radiationLabel.setStyleSheet("background-color: red; color: black;")
            else:
                self._radiationLabel.setText("UNKNOWN")
                self._radiationLabel.setStyleSheet("background-color: gray; color: black;")
                logger.warning("Radiation type {} is not supported ".format(selectedPlan.radiationType))

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
        calibration = readScanner(settings.scannerFolder)

#        self.selectedPlan.scoringVoxelSpacing = 3 * [self._doseSpacingSpin.value()]
        if self._radiationType.upper()=="PHOTON":
            doseCalculator = CCCDoseCalculator(batchSize= self._batchSize.value())
            doseCalculator.ctCalibration = calibration
            doseImage = doseCalculator.computeDose(self.selectedCT, self.selectedPlan)
            logger.info("Photon dose calculation is done. Check new generated dose image in patient data.")
            doseImage.patient = self.selectedCT.patient
        elif self._radiationType.upper()=="PROTON":
            doseCalculator = MCsquareDoseCalculator()
            beamModel = mcsquareIO.readBDL(settings.bdlFile)
            doseCalculator.beamModel = beamModel
            # self.selectedPlan.scoringVoxelSpacing = self._doseSpacingSpin.value()
            doseCalculator.setScoringParameters(scoringSpacing=self._doseSpacingSpin.value(), adapt_gridSize_to_new_spacing=True)
            doseCalculator.nbPrimaries = self._numProtons.value()
            doseCalculator.statUncertainty = self._statUncertainty.value()
            doseCalculator.ctCalibration = calibration
            doseCalculator.overwriteOutsideROI = self._selectedROI
            doseImage = doseCalculator.computeDose(self.selectedCT, self.selectedPlan)
            logger.info("Proton dose calculation is done. Check new generated dose image in patient data.")
            doseImage.patient = self.selectedCT.patient
        else:
            logger.error("Could not identify plan radiation type")


