from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QPushButton

from opentps.core.data.images import DoseImage
from opentps.core.data._patient import Patient
from opentps.gui.panels.patientDataWidgets import PatientDataComboBox


class DoseComparisonPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._dose1Label = QLabel('Dose 1:')
        self.layout.addWidget(self._dose1Label)
        self._dose1ComboBox = PatientDataComboBox(DoseImage, patient=self._patient, parent=self)
        self.layout.addWidget(self._dose1ComboBox)

        self._dose2Label = QLabel('Dose 2:')
        self.layout.addWidget(self._dose2Label)
        self._dose2ComboBox = PatientDataComboBox(DoseImage, patient=self._patient, parent=self)
        self.layout.addWidget(self._dose2ComboBox)

        self._runButton = QPushButton('Update!')
        self._runButton.clicked.connect(self._run)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    @property
    def _selectedDose1(self):
        return self._dose1ComboBox.selectedData

    @property
    def _selectedDose2(self):
        return self._dose2ComboBox.selectedData

    def setCurrentPatient(self, patient:Patient):
        self._patient = patient

        self._dose1ComboBox.setPatient(patient)
        self._dose2ComboBox.setPatient(patient)

    def _run(self):
        self._viewController.dose1 = self._selectedDose1
        self._viewController.dose2 = self._selectedDose2
