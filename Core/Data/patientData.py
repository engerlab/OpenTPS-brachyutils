import pydicom

from Core.Data.patientInfo import PatientInfo
from Core.api import API
from Core.event import Event


class PatientData:

    def __init__(self, patientInfo=None, name='', seriesInstanceUID=''):

        self.nameChangedSignal = Event(str)
        # self.setEvents()

        if(patientInfo == None):
            self.patientInfo = PatientInfo(patientID="Unknown", name="Unknown patient")
        else:
            self.patientInfo = patientInfo

        self._name = name
        self._patient = None

        if seriesInstanceUID:
            self.seriesInstanceUID = seriesInstanceUID
        else:
            self.seriesInstanceUID = pydicom.uid.generate_uid()


    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self.setName(name)

    @API.apiMethod
    def setName(self, name):
        self._name = name
        self.nameChangedSignal.emit(self._name)

    @property
    def patient(self):
        return self._patient

    @patient.setter
    def patient(self, patient):
        if patient == self._patient:
            return

        self._patient = patient

        if not(self._patient is None):
            self._patient.appendPatienData(self)

    def getType(self):
        return self.__class__.__name__