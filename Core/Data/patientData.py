from Core.Data.patientInfo import PatientInfo

class PatientData:

    def __init__(self, patientInfo=None):
        if(patientInfo == None):
            self.patientInfo = PatientInfo(patientID="Unknown", name="Unknown patient")
        else:
            self.patientInfo = patientInfo