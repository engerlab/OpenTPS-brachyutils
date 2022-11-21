from PyQt5.QtWidgets import QComboBox
from opentps.core import Event
from opentps.core.data import Patient, PatientData


class PatientDataComboBox(QComboBox):
    def __init__(self, patientDataType, patient=None, parent=None):
        super().__init__(parent=parent)

        self.selectedDataEvent = Event()

        self._prevEventData = None

        self._patient = None
        self._patientDataType = patientDataType
        self._patientData = []

        self.currentIndexChanged.connect(self._handleNewData)
        self.currentTextChanged.connect(self._handleNewData)

        self.setPatient(patient)

    def closeEvent(self, QCloseEvent):
        self.setPatient(None)

        super().closeEvent(QCloseEvent)

    def _handleNewData(self):
        if self._prevEventData == self.selectedData:
            return

        self._prevEventData = self.selectedData
        self.selectedDataEvent.emit(self.selectedData)

    def setPatient(self, patient:Patient):
        if not (self._patient is None):
            self._patient.patientDataAddedSignal.disconnect(self._addData)
            self._patient.patientDataRemovedSignal.disconnect(self._removeData)

        self._patient = patient

        if self._patient is None:
            pass
        else:
            self._patient.patientDataAddedSignal.connect(self._addData)
            self._patient.patientDataRemovedSignal.connect(self._removeData)

            self._updateComboBox()

    @property
    def selectedData(self):
        if len(self._patientData)==0:
            return

        return self._patientData[self.currentIndex()]

    @selectedData.setter
    def selectedData(self, data):
        if len(self._patientData)==0:
            return

        try:
            currentIndex = self._patientData.index(data)
            self.setCurrentIndex(currentIndex)
        except:
            self.setCurrentIndex(0)
            if len(self._patientData):
                self.selectedData = self._patientData[0]

        self._handleNewData()

    def _updateComboBox(self):
        if self._checkIfSelfDeleted():
            return

        selectedData = self.selectedData

        self._removeAllData()

        for data in self._patient.getPatientDataOfType(self._patientDataType):
            self._addData(data)

        self.selectedData = selectedData


    def _addData(self, data:PatientData):
        if self._checkIfSelfDeleted():
            return

        if not(isinstance(data, self._patientDataType)):
            return

        self.addItem(data.name, data)
        self._patientData.append(data)
        data.nameChangedSignal.connect(self._handleDataChanged)

        self._handleNewData()

    def _removeData(self, data:PatientData):
        if self._checkIfSelfDeleted():
            return

        if not(isinstance(data, self._patientDataType)):
            return

        selectedData = self.selectedData

        data.nameChangedSignal.disconnect(self._handleDataChanged)
        self.removeItem(self.findData(data))
        self._patientData.remove(data)

        self.selectedData = selectedData

    def _removeAllData(self):
        for data in self._patientData:
            self._removeData(data)

    def _handleDataChanged(self, data):
        self._updateComboBox()

    def _checkIfSelfDeleted(self):
        try:
            self.findData(None)
        except:
            self.setPatient(None)
            return True

        return False
