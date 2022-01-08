import pydicom

from Core.Data.patientInfo import PatientInfo

class PatientData:

    def __init__(self, patientInfo=None, name='', seriesInstanceUID=''):

        if(patientInfo == None):
            self.patientInfo = PatientInfo(patientID="Unknown", name="Unknown patient")
        else:
            self.patientInfo = patientInfo

        self.name = name

        if seriesInstanceUID:
            self.seriesInstanceUID = seriesInstanceUID
        else:
            self.seriesInstanceUID = pydicom.uid.generate_uid()

    def getType(self):
        return self.__class__.__name__
