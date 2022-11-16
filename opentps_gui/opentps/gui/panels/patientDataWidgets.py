from PyQt5.QtWidgets import QComboBox
from opentps.core.data import Patient, PatientData


class PatientDataComboBox(QComboBox):
    def __init__(self, patientDataType, patient=None, parent=None):
        super().__init__(parent=parent)

        self._patient = None
        self._patientDataType = patientDataType
        self._patientData = []

        self.setPatient(patient)

    def setPatient(self, patient:Patient):
        if not (self._patient is None):
            self._patient.patientDataAddedSignal.disconnect(self._handleDataAddedOrRemoved)
            self._patient.patientDataAddedSignal.disconnect(self._handleDataAddedOrRemoved)

        self._patient = patient

        if self._patient is None:
            pass
        else:
            self._patient.patientDataAddedSignal.connect(self._handleDataAddedOrRemoved)
            self._patient.patientDataAddedSignal.connect(self._handleDataAddedOrRemoved)

            self._updateComboBox()

    @property
    def selectedData(self):
        return self._patientData[self.currentIndex()]

    @selectedData.setter
    def selectedData(self, data):
        self.setCurrentIndex(self._patientData.index(data))

    def _updateComboBox(self):
        self._removeAllData()

        for data in self._patient.getPatientDataOfType(self._patientDataType):
            self._addData(data)

        try:
            currentIndex = self._patientData.index(self.selectedData)
            self.setCurrentIndex(currentIndex)
        except:
            self.setCurrentIndex(0)
            if len(self._patientData):
                self.selectedData = self._patientData[0]

    def _addData(self, data:PatientData):
        self.addItem(data.name, data)
        self._patientData.append(data)
        data.nameChangedSignal.connect(self._handleDataChanged)

    def _removeData(self, data:PatientData):
        data.nameChangedSignal.disconnect(self._handleDataChanged)
        self.removeItem(self.findData(data))
        self._patientData.remove(data)

    def _removeAllData(self):
        for data in self._patientData:
            self._removeData(data)

    def _handleDataAddedOrRemoved(self, data):
        self._updateComboBox()

    def _handleDataChanged(self, data):
        self._updateComboBox()
