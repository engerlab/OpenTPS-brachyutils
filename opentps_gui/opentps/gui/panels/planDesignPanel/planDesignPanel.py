from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDoubleSpinBox, QListWidget, \
    QHBoxLayout, QMenu, QAction

from opentps.core.data.plan._planDesign import PlanDesign
from opentps.core.data._patient import Patient
from opentps.core.io import mcsquareIO
from opentps.core.io.mcsquareIO import readBDL
from opentps.core.io.scannerReader import readScanner
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.gui.panels.planDesignPanel.beamDialog import BeamDialog
from opentps.gui.panels.planDesignPanel.robustnessSettings import RobustnessSettings


class PlanDesignPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._beamDescription = []

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._planLabel = QLabel('plan name:')
        self.layout.addWidget(self._planLabel)
        self._planNameEdit = QLineEdit(self)
        self._planNameEdit.setText('New plan')
        self.layout.addWidget(self._planNameEdit)

        from opentps.gui.programSettingEditor import MCsquareConfigEditor
        self._mcsquareConfigWidget = MCsquareConfigEditor(self)
        self._mcsquareConfigWidget.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self._mcsquareConfigWidget)

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

        self._beams = QListWidget()
        self._beams.setContextMenuPolicy(Qt.CustomContextMenu)
        self._beams.customContextMenuRequested.connect(lambda pos, list_type='beam': self.List_RightClick(pos, list_type))
        self.layout.addWidget(self._beams)

        self._beamButton = QPushButton('Add beam')
        self.layout.addWidget(self._beamButton)
        self._beamButton.clicked.connect(self.add_new_beam)


        self._robustnessSettingsButton = QPushButton('Modify robustness settings')
        self._robustnessSettingsButton.clicked.connect(self._openRobustnessSettings)
        self.layout.addWidget(self._robustnessSettingsButton)

        self._robustSettingsLabel = QLabel('')
        self.layout.addWidget(self._robustSettingsLabel)

        self._runButton = QPushButton('Design plan')
        self._runButton.clicked.connect(self._create)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    def setCurrentPatient(self, patient:Patient):
        self._patient = patient

    def _create(self):
        planDesign = PlanDesign()
        planDesign.spotSpacing = self._spacingSpin.value()
        planDesign.layerSpacing = self._layerSpin.value()
        planDesign.targetMargin = self._marginSpin.value()

        planDesign.name = self._planNameEdit.text()

        planDesign.patient = self._patient

        settings = DoseCalculationConfig()
        beamModel = mcsquareIO.readBDL(settings.bdlFile)
        calibration = readScanner(settings.scannerFolder)
        planDesign.calibration = calibration

        # extract beam info from QListWidget
        beamNames = []
        gantryAngles = []
        couchAngles = []
        rangeShifters = []
        AlignLayers = False
        for i in range(self._beams.count()):
            BeamType = self.beamDescription[i]["BeamType"]
            if (BeamType == "beam"):
                beamNames.append(self.beamDescription[i]["BeamName"])
                gantryAngles.append(self.beamDescription[i]["GantryAngle"])
                couchAngles.append(self.beamDescription[i]["CouchAngle"])
                RS_ID = self.beamDescription[i]["RangeShifter"]
                if (RS_ID == "None"):
                    RangeShifter = "None"
                else:
                    RangeShifter = next((RS for RS in beamModel.rangeShifters if RS.ID == RS_ID), -1)
                    if (RangeShifter == -1):
                        print("WARNING: Range shifter " + RS_ID + " was not found in the BDL.")
                        RangeShifter = "None"
                rangeShifters.append(RangeShifter)

        planDesign.gantryAngles = gantryAngles
        planDesign.beamNames = beamNames
        planDesign.couchAngles = couchAngles
        planDesign.rangeShifters = rangeShifters

    def add_new_beam(self):
        beam_number = self._beams.count()

        # retrieve list of range shifters from BDL
        bdl = readBDL(DoseCalculationConfig().bdlFile)
        RangeShifterList = [rs.ID for rs in bdl.rangeShifters]

        dialog = BeamDialog("Beam " + str(beam_number + 1), RangeShifterList=RangeShifterList)
        if (dialog.exec()):
            BeamName = dialog.BeamName.text()
            GantryAngle = dialog.GantryAngle.value()
            CouchAngle = dialog.CouchAngle.value()
            RangeShifter = dialog.RangeShifter.currentText()

            if (RangeShifter == "None"):
                RS_disp = ""
            else:
                RS_disp = ", RS"
            self._beams.addItem(BeamName + ":  G=" + str(GantryAngle) + "°,  C=" + str(CouchAngle) + "°" + RS_disp)
            self.beamDescription.append(
                {"BeamType": "beam", "BeamName": BeamName, "GantryAngle": GantryAngle, "CouchAngle": CouchAngle,
                 "RangeShifter": RangeShifter})


    def _openRobustnessSettings(self):
        dialog = RobustnessSettings(planEvaluation=False)
        if (dialog.exec()):
            self._robustParam = dialog.robustParam

        self._updateRobustSettings()

    def _updateRobustSettings(self):
        if (self._robustParam.strategy == self._robustParam.Strategies.DISABLED):
            self._robustParam.setText('Disabled')
        else:
            RobustSettings = ''
            RobustSettings += 'Selection: error space<br>'
            RobustSettings += 'Syst. setup: E<sub>S</sub> = ' + str(self._robustParam.systSetup) + ' mm<br>'
            RobustSettings += 'Rand. setup: &sigma;<sub>S</sub> = ' + str(self._robustParam.randSetup) + ' mm<br>'
            RobustSettings += 'Syst. range: E<sub>R</sub> = ' + str(self._robustParam.systRange) + ' %'
            self._robustSettingsLabel.setText(RobustSettings)

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
            self.BeamDescription.pop(row)

