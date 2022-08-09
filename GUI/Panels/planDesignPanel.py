
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDoubleSpinBox

from Core.Data.Plan.planStructure import PlanStructure
from Core.Data.patient import Patient

class PlanDesignPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._planLabel = QLabel('Plan name:')
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

        self._runButton = QPushButton('Create')
        self._runButton.clicked.connect(self._create)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    def setCurrentPatient(self, patient:Patient):
        self._patient = patient

    def _create(self):
        planStructure = PlanStructure()
        planStructure.spotSpacing = self._spacingSpin.value()
        planStructure.layerSpacing = self._layerSpin.value()
        planStructure.targetMargin = self._marginSpin.value()

        planStructure.patient = self._patient
        planStructure.name = self._planNameEdit.text()
