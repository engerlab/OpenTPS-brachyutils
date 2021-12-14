
class PatientList():
    def __init__(self):
        self.list = []

    def __getitem__(self, index):
        return self.list[index]

    def __len__(self):
        return len(self.list)

    def append(self, patient):
        self.list.append(patient)

    def getPatientByPatientId(self, id):
        for i, patient in enumerate(self.list):
            if patient.patientID==id:
                return self.list[i]

    def remove(self, patient):
        self.list.remove(patient)
