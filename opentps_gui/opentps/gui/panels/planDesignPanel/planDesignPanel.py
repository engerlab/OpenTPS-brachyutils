import logging
import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDoubleSpinBox, QListWidget, \
    QHBoxLayout, QMenu, QAction

from opentps.core.data.plan._planDesign import PlanDesign
from opentps.core.data._patient import Patient
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

        self._planLabel = QLabel('plan name:')
        self.layout.addWidget(self._planLabel)
        self._planNameEdit = QLineEdit(self)
        self._planNameEdit.setText('New plan design')
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

        self._robustSettings = RobustnessSettings(self._viewController, parent=self)
        self.layout.addWidget(self._robustSettings)

        self._runButton = QPushButton('Design plan')
        self._runButton.clicked.connect(self._create)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    def setCurrentPatient(self, patient:Patient):
        self._patient = patient

    def _create(self):
        logger.info('Plan is designed...')
        start = time.time()
        planDesign = PlanDesign()
        planDesign.spotSpacing = self._spacingSpin.value()
        planDesign.layerSpacing = self._layerSpin.value()
        planDesign.targetMargin = self._marginSpin.value()

        planDesign.name = self._planNameEdit.text()

        planDesign.patient = self._patient

        settings = DoseCalculationConfig()
        beamModel = mcsquareIO.readBDL(settings.bdlFile)

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
                rs = self._beamDescription[i]["RangeShifter"]
                rangeShifters.append(rs)

        planDesign.gantryAngles = gantryAngles
        planDesign.beamNames = beamNames
        planDesign.couchAngles = couchAngles
        planDesign.rangeShifters = rangeShifters

        planDesign.robustness = self._robustSettings.robustness
        logger.info("New plan design created in {} sec".format(time.time() - start))

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

