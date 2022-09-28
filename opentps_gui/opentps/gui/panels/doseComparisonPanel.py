from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QLabel, QPushButton

from opentps.core.data.images import DoseImage
from opentps.core.data._patient import Patient


class DoseComparisonPanel(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._patient:Patient = None
        self._viewController = viewController
        self._doseImages = []
        self._selectedDose1 = None
        self._selectedDose2 = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._dose1Label = QLabel('Dose 1:')
        self.layout.addWidget(self._dose1Label)
        self._dose1ComboBox = QComboBox(self)
        self._dose1ComboBox.currentIndexChanged.connect(self._handleDose1Index)
        self.layout.addWidget(self._dose1ComboBox)

        self._dose2Label = QLabel('Dose 2:')
        self.layout.addWidget(self._dose2Label)
        self._dose2ComboBox = QComboBox(self)
        self._dose2ComboBox.currentIndexChanged.connect(self._handleDose2Index)
        self.layout.addWidget(self._dose2ComboBox)

        self._runButton = QPushButton('Update!')
        self._runButton.clicked.connect(self._run)
        self.layout.addWidget(self._runButton)

        self.layout.addStretch()

        self.setCurrentPatient(self._viewController.currentPatient)
        self._viewController.currentPatientChangedSignal.connect(self.setCurrentPatient)

    def _handleDose1Index(self, *args):
        self._selectedDose1 = self._doseImages[self._dose1ComboBox.currentIndex()]

    def _handleDose2Index(self, *args):
        self._selectedDose2 = self._doseImages[self._dose2ComboBox.currentIndex()]

    def setCurrentPatient(self, patient:Patient):
        if not (self._patient is None):
            self._patient.imageAddedSignal.disconnect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.disconnect(self._handleImageAddedOrRemoved)

        self._patient = patient

        if self._patient is None:
            self._removeAllDoses()
        else:
            self._patient.imageAddedSignal.connect(self._handleImageAddedOrRemoved)
            self._patient.imageRemovedSignal.connect(self._handleImageAddedOrRemoved)

            self._updateDoseComboBoxes()

    def _updateDoseComboBoxes(self):
        self._removeAllDoses()

        self._doseImages = [dose for dose in self._patient.getPatientDataOfType(DoseImage)]

        for dose in self._doseImages:
            self._addDose1(dose)
            self._addDose2(dose)

        try:
            currentIndex = self._doseImages.index(self._selectedDose1)
            self._dose1ComboBox.setCurrentIndex(currentIndex)
        except:
            self._dose1ComboBox.setCurrentIndex(0)
            if len(self._doseImages):
                self._selectedDose1 = self._doseImages[0]

        try:
            currentIndex = self._doseImages.index(self._selectedDose2)
            self._dose2ComboBox.setCurrentIndex(currentIndex)
        except:
            self._dose2ComboBox.setCurrentIndex(0)
            if len(self._doseImages):
                self._selectedDose2 = self._doseImages[0]

    def _removeAllDoses(self):
        for dose in self._doseImages:
            self._removeDose(dose)

    def _addDose1(self, dose:DoseImage):
        self._dose1ComboBox.addItem(dose.name, dose)
        dose.nameChangedSignal.connect(self._handleDoseChanged)

    def _addDose2(self, dose: DoseImage):
        self._dose2ComboBox.addItem(dose.name, dose)
        dose.nameChangedSignal.connect(self._handleDoseChanged)

    def _removeDose(self, dose:DoseImage):
        dose.nameChangedSignal.disconnect(self._handleDoseChanged)

        if dose==self._selectedDose1:
            self._selectedDose1 = None

        if dose==self._selectedDose2:
            self._selectedDose2 = None

        self._dose1ComboBox.removeItem(self._dose2ComboBox.findData(dose))
        self._dose2ComboBox.removeItem(self._dose2ComboBox.findData(dose))

    def _handleImageAddedOrRemoved(self, image):
        self._updateDoseComboBoxes()

    def _handleDoseChanged(self, dose):
        self._updateDoseComboBoxes()

    def _run(self):
        self._viewController.dose1 = self._selectedDose1
        self._viewController.dose2 = self._selectedDose2
