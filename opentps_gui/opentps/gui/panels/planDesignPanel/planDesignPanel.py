import logging
import time
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDoubleSpinBox, QListWidget, \
    QHBoxLayout, QMenu, QAction, QComboBox

from opentps.core.data.plan._protonPlanDesign import ProtonPlanDesign
from opentps.core.data._patient import Patient
from opentps.core.data.plan._photonPlanDesign import PhotonPlanDesign
from opentps.core.io import mcsquareIO
from opentps.core.io.mcsquareIO import readBDL
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.gui.panels.planDesignPanel.beamDialog import BeamDialog
from opentps.gui.panels.planDesignPanel.robustnessSettings import RobustnessSettings

logger = logging.getLogger(__name__)

class PlanDesignPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._beamDescription = []

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._modalityLabel = QLabel('Modality:')
        self.layout.addWidget(self._modalityLabel)
        self._modalityComboBox = QComboBox(self)
        self._modalityComboBox.addItem("IMPT")
        self._modalityComboBox.addItem("IMRT")
        self.layout.addWidget(self._modalityComboBox)
        
        self._planLabel = QLabel('Plan name:')
        self.layout.addWidget(self._planLabel)

        self._planIMPTNameEdit = QLineEdit(self)
        self._planIMPTNameEdit.setText('New IMPT plan design')
        self.layout.addWidget(self._planIMPTNameEdit)
        self._planIMRTNameEdit = QLineEdit(self)
        self._planIMRTNameEdit.setText('New IMRT plan design')
        self.layout.addWidget(self._planIMRTNameEdit)
        self._planIMRTNameEdit.hide()

        from opentps.gui.programSettingEditor import MCsquareConfigEditor
        self._mcsquareConfigWidget = MCsquareConfigEditor(self)
        self._mcsquareConfigWidget.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self._mcsquareConfigWidget)

        self._xBeamletSpacingLayout = QHBoxLayout()
        self.layout.addLayout(self._xBeamletSpacingLayout)
        self.xBeamletSpacingLabel = QLabel('Beamlet spacing X:')
        self._xBeamletSpacingLayout.addWidget(self.xBeamletSpacingLabel)
        self._xBeamletSpacing = QDoubleSpinBox()
        self._xBeamletSpacing.setGroupSeparatorShown(True)
        self._xBeamletSpacing.setRange(0.1, 100.0)
        self._xBeamletSpacing.setSingleStep(1.0)
        self._xBeamletSpacing.setValue(5.0)
        self._xBeamletSpacing.setSuffix(" mm")
        self._xBeamletSpacingLayout.addWidget(self._xBeamletSpacing)
        self._yBeamletSpacingLayout = QHBoxLayout()
        self.layout.addLayout(self._yBeamletSpacingLayout)
        self.yBeamletSpacingLabel = QLabel('Beamlet spacing Y:')
        self._yBeamletSpacingLayout.addWidget(self.yBeamletSpacingLabel)
        self._yBeamletSpacing = QDoubleSpinBox()
        self._yBeamletSpacing.setGroupSeparatorShown(True)
        self._yBeamletSpacing.setRange(0.1, 100.0)
        self._yBeamletSpacing.setSingleStep(1.0)
        self._yBeamletSpacing.setValue(5.0)
        self._yBeamletSpacing.setSuffix(" mm")
        self._yBeamletSpacingLayout.addWidget(self._yBeamletSpacing)

        self.xBeamletSpacingLabel.hide()
        self._xBeamletSpacing.hide()
        self.yBeamletSpacingLabel.hide()
        self._yBeamletSpacing.hide()

        self._spacingLayout = QHBoxLayout()
        self.layout.addLayout(self._spacingLayout)
        self._spacingLabel = QLabel('Spot spacing:')
        self._spacingLayout.addWidget(self._spacingLabel)
        self._spacingSpin = QDoubleSpinBox()
        self._spacingSpin.setGroupSeparatorShown(True)
        self._spacingSpin.setRange(0.1, 100.0)
        self._spacingSpin.setSingleStep(1.0)
        self._spacingSpin.setValue(5.0)
        self._spacingSpin.setSuffix(" mm")
        self._spacingLayout.addWidget(self._spacingSpin)

        self._layerLayout = QHBoxLayout()
        self.layout.addLayout(self._layerLayout)

        self._layerLabel = QLabel('Layer spacing:')
        self._layerLayout.addWidget(self._layerLabel)
        self._layerSpin = QDoubleSpinBox()
        self._layerSpin.setGroupSeparatorShown(True)
        self._layerSpin.setRange(0.1, 100.0)
        self._layerSpin.setSingleStep(1.0)
        self._layerSpin.setValue(2.0)
        self._layerSpin.setSuffix(" mm")
        self._layerLayout.addWidget(self._layerSpin)

        self._marginLayout = QHBoxLayout()
        self.layout.addLayout(self._marginLayout)

        self._marginLabel = QLabel('Target margin:')
        self._marginLayout.addWidget(self._marginLabel)
        self._marginSpin = QDoubleSpinBox()
        self._marginSpin.setGroupSeparatorShown(True)
        self._marginSpin.setRange(0.1, 100.0)
        self._marginSpin.setSingleStep(1.0)
        self._marginSpin.setValue(5.0)
        self._marginSpin.setSuffix(" mm")
        self._marginLayout.addWidget(self._marginSpin)

        self._proximalLayout = QHBoxLayout()
        self.layout.addLayout(self._proximalLayout)

        self._proximalLabel = QLabel('Proximal layers:')
        self._proximalLayout.addWidget(self._proximalLabel)
        self._proximalSpin = QDoubleSpinBox()
        self._proximalSpin.setGroupSeparatorShown(True)
        self._proximalSpin.setRange(0, 100)
        self._proximalSpin.setSingleStep(1)
        self._proximalSpin.setValue(1)
        self._proximalSpin.setDecimals(0)
        self._proximalLayout.addWidget(self._proximalSpin)

        self._distalLayout = QHBoxLayout()
        self.layout.addLayout(self._distalLayout)

        self._distalLabel = QLabel('Distal layers:')
        self._distalLayout.addWidget(self._distalLabel)
        self._distalSpin = QDoubleSpinBox()
        self._distalSpin.setGroupSeparatorShown(True)
        self._distalSpin.setRange(0, 1)
        self._distalSpin.setSingleStep(1)
        self._distalSpin.setValue(1)
        self._distalSpin.setDecimals(0)
        self._distalLayout.addWidget(self._distalSpin)

        self._isocenterLayout = QHBoxLayout()
        self.layout.addLayout(self._isocenterLayout)

        self._isocenterLabel = QLabel('Isocenter:')
        self._isocenterLayout.addWidget(self._isocenterLabel)
        self._isocenterComboBox = QComboBox(self)
        self._isocenterComboBox.addItem("Target COM")
        self._isocenterComboBox.addItem("Custom")
        self._isocenterLayout.addWidget(self._isocenterComboBox)
        self._isocenterCustomInput = QLineEdit(self)
        self._isocenterCustomInput.setPlaceholderText("(a,b,c) mm")
        self._isocenterCustomInput.hide()
        self._isocenterLayout.addWidget(self._isocenterCustomInput)
        self._isocenterComboBox.currentTextChanged.connect(self._toggleIsocenterInput)

        self._beams = QListWidget()
        self._beams.setContextMenuPolicy(Qt.CustomContextMenu)
        self._beams.customContextMenuRequested.connect(lambda pos, list_type='beam': self.List_RightClick(pos, list_type))
        self.layout.addWidget(self._beams)

        self._beamButton = QPushButton('Add beam')
        self.layout.addWidget(self._beamButton)
        self._beamButton.clicked.connect(self.add_new_beam)

        self._robustSettings = RobustnessSettings(self._viewController, parent=self)
        self.layout.addWidget(self._robustSettings)

        self._runButton = QPushButton('Design plan')
        self._runButton.clicked.connect(self._create)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._modalityComboBox.currentTextChanged.connect(self.updateUIBasedOnModality)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    def _toggleIsocenterInput(self, text):
        if text == "Custom":
            self._isocenterCustomInput.show()
        else:
            self._isocenterCustomInput.hide()

    @property
    def selectedModality(self):
        return self._modalityComboBox.currentText()
    
    @selectedModality.setter
    def selectedModality(self, modality):
        self._modalityComboBox.setCurrentText(modality)
    
    def updateUIBasedOnModality(self,modality):
        if modality == "IMRT":
            self._mcsquareConfigWidget._txt2.hide()
            self._spacingLabel.hide()
            self._spacingSpin.hide()
            self._layerLabel.hide()
            self._layerSpin.hide()
            self._proximalLabel.hide()
            self._proximalSpin.hide()
            self._distalLabel.hide()
            self._distalSpin.hide()
            self._planIMPTNameEdit.hide()

            self.xBeamletSpacingLabel.show()
            self._xBeamletSpacing.show()
            self.yBeamletSpacingLabel.show()
            self._yBeamletSpacing.show()
            self._planIMRTNameEdit.show()

        elif modality == "IMPT":
            self._mcsquareConfigWidget._txt2.show()
            self._spacingLabel.show()
            self._spacingSpin.show()
            self._layerLabel.show()
            self._layerSpin.show()
            self._proximalLabel.show()
            self._proximalSpin.show()
            self._distalLabel.show()
            self._distalSpin.show()
            self._planIMPTNameEdit.show()

            self.xBeamletSpacingLabel.hide()
            self._xBeamletSpacing.hide()
            self.yBeamletSpacingLabel.hide()
            self._yBeamletSpacing.hide()
            self._planIMRTNameEdit.hide()

        for _ in range(self._beams.count()):
            self.delete_item('beam', 0)

        self._robustSettings._updateForModality(modality)

    def setCurrentPatient(self, patient:Patient):
        self._patient = patient

    def _create(self):
        logger.info('Plan is designed...')
        start = time.time()

        if self.selectedModality == "IMRT":
            planDesign = PhotonPlanDesign()
            planDesign.xBeamletSpacing_mm = self._xBeamletSpacing.value()
            planDesign.yBeamletSpacing_mm = self._yBeamletSpacing.value()
            planDesign.name = self._planIMRTNameEdit.text()

        elif self.selectedModality == "IMPT":
            planDesign = ProtonPlanDesign()
            planDesign.spotSpacing = self._spacingSpin.value()
            planDesign.layerSpacing = self._layerSpin.value()
            planDesign.name = self._planIMPTNameEdit.text()
            
        else:
            logger.error(f"Unsupported modality: {self.selectedModality}")

        planDesign.targetMargin = self._marginSpin.value()
        planDesign.patient = self._patient

        # Isocentre
        isocenter_option = self._isocenterComboBox.currentText()
        if isocenter_option == "Target COM":
            planDesign.isocenterPosition_mm = None
        elif isocenter_option == "Custom":
            try:
                custom_isocenter = eval(self._isocenterCustomInput.text())
                if isinstance(custom_isocenter, (list, tuple)) and len(custom_isocenter) == 3:
                    planDesign.isocenterPosition_mm = np.array(custom_isocenter)
                else:
                    raise ValueError("Invalid format for isocenter")
            except Exception as e:
                logger.error(f"Invalid isocenter input: {e}")
                return
        else:
            logger.error(f"Unsupported isocenter option: {isocenter_option}")

        # extract beam info from QListWidget
        beamNames = []
        gantryAngles = []
        couchAngles = []
        rangeShifters = []
        AlignLayers = False
        for i in range(self._beams.count()):
            BeamType = self._beamDescription[i]["BeamType"]
            if (BeamType == "beam"):
                beamNames.append(self._beamDescription[i]["BeamName"])
                gantryAngles.append(self._beamDescription[i]["GantryAngle"])
                couchAngles.append(self._beamDescription[i]["CouchAngle"])
                if self.selectedModality == "IMPT":
                    rs = self._beamDescription[i]["RangeShifter"]
                    rangeShifters.append(rs)

        planDesign.gantryAngles = gantryAngles
        planDesign.beamNames = beamNames
        planDesign.couchAngles = couchAngles
        if self.selectedModality == "IMPT": planDesign.rangeShifters = rangeShifters
        
        planDesign.robustness = self._robustSettings.robustness
        logger.info("New plan design created in {} sec".format(time.time() - start))

    def add_new_beam(self):
        beam_number = self._beams.count()

        # retrieve list of range shifters from BDL
        if self.selectedModality == "IMPT":
            bdl = readBDL(DoseCalculationConfig().bdlFile)
            RangeShifterList = [rs.ID for rs in bdl.rangeShifters]
        else: RangeShifterList=[]

        dialog = BeamDialog(self.selectedModality, "Beam " + str(beam_number + 1), RangeShifterList=RangeShifterList)
        if (dialog.exec()):
            BeamName = dialog.BeamName.text()
            GantryAngle = dialog.GantryAngle.value()
            CouchAngle = dialog.CouchAngle.value()
            if self.selectedModality == "IMPT":
                RangeShifter = dialog.RangeShifter.currentText()
                if (RangeShifter == "None"):
                    RS_disp = ""
                    rs = None
                else:
                    RS_disp = ", RS"
                    rs = [rsElem for rsElem in bdl.rangeShifters if rsElem.ID==RangeShifter]
                    if len(rs)==0:
                        rs = None
                    else:
                        rs = rs[0]
                self._beams.addItem(BeamName + ":  G=" + str(GantryAngle) + "°,  C=" + str(CouchAngle) + "°" + RS_disp)
                self._beamDescription.append(
                    {"BeamType": "beam", "BeamName": BeamName, "GantryAngle": GantryAngle, "CouchAngle": CouchAngle,
                    "RangeShifter": rs})
            else:
                self._beams.addItem(BeamName + ":  G=" + str(GantryAngle) + "°,  C=" + str(CouchAngle) + "°")
                self._beamDescription.append(
                    {"BeamType": "beam", "BeamName": BeamName, "GantryAngle": GantryAngle, "CouchAngle": CouchAngle})


    def List_RightClick(self, pos, list_type):
        if list_type == 'beam':
            item = self._beams.itemAt(pos)
            row = self._beams.row(item)
            pos = self._beams.mapToGlobal(pos)

        else:
            return

        if row > -1:
            self.context_menu = QMenu()
            self.delete_action = QAction("Delete")
            self.delete_action.triggered.connect(
                lambda checked, list_type=list_type, row=row: self.delete_item(list_type, row))
            self.context_menu.addAction(self.delete_action)
            self.context_menu.popup(pos)

    def delete_item(self, list_type, row):
        if list_type == 'beam':
            self._beams.takeItem(row)
            self._beamDescription.pop(row)

