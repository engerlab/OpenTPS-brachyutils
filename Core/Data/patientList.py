from Core.event import Event


class PatientList():
    def __init__(self):
        self.patientAddedSignal = Event(object)
        self.patientRemovedSignal = Event(object)

        self._patients = []

    def __getitem__(self, index):
        return self._patients[index]

    def __len__(self):
        return len(self._patients)

    @property
    def patients(self):
        # Doing this ensures that the user can't append directly to patients
        return [patient for patient in self._patients]

    def append(self, patient):
        self._patients.append(patient)
        self.patientAddedSignal.emit(self._patients[-1])

    def getIndex(self, patient):
        return self._patients.index(patient)

    def getIndexFromPatientID(self, patientID):
        if patientID == "":
            return -1

        index = next((x for x, val in enumerate(self._patients) if val.patientInfo.patientID == patientID), -1)
        return index

    def getIndexFromPatientName(self, patientName):
        if patientName == "":
            return -1

        index = next((x for x, val in enumerate(self._patients) if val.patientInfo.name == patientName), -1)
        return index

    def getPatientByData(self, patientData):
        for patient in self._patients:
            if patient.hasPatientData(patientData):
                return patient

        return None

    def getPatientByPatientId(self, id):
        for i, patient in enumerate(self._patients):
            if patient.patientInfo.patientID==id:
                return patient

    def remove(self, patient):
        self._patients.remove(patient)
        self.patientRemovedSignal.emit(patient)
