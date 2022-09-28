
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDoubleSpinBox

from opentps.core.data.plan._planDesign import PlanDesign
from opentps.core.data._patient import Patient
from opentps.gui.panels.planDesignPanel.robustnessSettings import RobustnessSettings


class PlanDesignPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._planLabel = QLabel('plan name:')
        self.layout.addWidget(self._planLabel)
        self._planNameEdit = QLineEdit(self)
        self._planNameEdit.setText('New plan')
        self.layout.addWidget(self._planNameEdit)

        self._spacingLabel = QLabel('Spot spacing:')
        self.layout.addWidget(self._spacingLabel)
        self._spacingSpin = QDoubleSpinBox()
        self._spacingSpin.setGroupSeparatorShown(True)
        self._spacingSpin.setRange(0.1, 100.0)
        self._spacingSpin.setSingleStep(1.0)
        self._spacingSpin.setValue(5.0)
        self._spacingSpin.setSuffix(" mm")
        self.layout.addWidget(self._spacingSpin)

        self._layerLabel = QLabel('Layer spacing:')
        self.layout.addWidget(self._layerLabel)
        self._layerSpin = QDoubleSpinBox()
        self._layerSpin.setGroupSeparatorShown(True)
        self._layerSpin.setRange(0.1, 100.0)
        self._layerSpin.setSingleStep(1.0)
        self._layerSpin.setValue(2.0)
        self._layerSpin.setSuffix(" mm")
        self.layout.addWidget(self._layerSpin)

        self._marginLabel = QLabel('Target margin:')
        self.layout.addWidget(self._marginLabel)
        self._marginSpin = QDoubleSpinBox()
        self._marginSpin.setGroupSeparatorShown(True)
        self._marginSpin.setRange(0.1, 100.0)
        self._marginSpin.setSingleStep(1.0)
        self._marginSpin.setValue(5.0)
        self._marginSpin.setSuffix(" mm")
        self.layout.addWidget(self._marginSpin)

        self._anglesLabel = QLabel('Gantry angles:')
        self.layout.addWidget(self._anglesLabel)
        self._anglesEdit = QLineEdit(self)
        self._anglesEdit.setPlaceholderText('0;45')
        self.layout.addWidget(self._anglesEdit)

        self._couchAnglesLabel = QLabel('Couch angles:')
        self.layout.addWidget(self._couchAnglesLabel)
        self._couchAnglesEdit = QLineEdit(self)
        self._couchAnglesEdit.setText('0')
        self.layout.addWidget(self._couchAnglesEdit)

        self._robustnessSettingsButton = QPushButton('Modify robustness settings')
        self._robustnessSettingsButton.clicked.connect(self._openRobustnessSettings)
        self.layout.addWidget(self._robustnessSettingsButton)

        self._robustSettingsLabel = QLabel('')
        self.layout.addWidget(self._robustSettingsLabel)

        self._runButton = QPushButton('Create')
        self._runButton.clicked.connect(self._create)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    def setCurrentPatient(self, patient:Patient):
        self._patient = patient

    def _create(self):
        planStructure = PlanDesign()
        planStructure.spotSpacing = self._spacingSpin.value()
        planStructure.layerSpacing = self._layerSpin.value()
        planStructure.targetMargin = self._marginSpin.value()

        gantryAnglesStr = self._anglesEdit.text().split(";")
        gantryAngles = [float(angle) for angle in gantryAnglesStr]

        planStructure.gantryAngles = gantryAngles

        couchAnglesStr = self._couchAnglesEdit.text().split(";")
        couchAngles = [float(angle) for angle in couchAnglesStr]

        if len(couchAngles)==1 and couchAngles==0.:
            couchAngles = [0 for angle in couchAngles]

        if len(gantryAngles) != len(couchAngles):
            raise Exception("The number of gantry angles must be equal to the number of couch angles")

        planStructure.couchAngles = couchAngles

        planStructure.name = self._planNameEdit.text()

        planStructure.patient = self._patient

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
