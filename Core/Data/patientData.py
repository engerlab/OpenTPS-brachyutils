import copy
import unittest

import pydicom

from Core.Data.patientInfo import PatientInfo
from Core.api import API
from Core.event import Event


class PatientData:

    def __init__(self, patientInfo=None, patient=None, name='', seriesInstanceUID=''):

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

    def deepCopyWithoutEvent(self):
        newObj = copy.deepcopy(self)
        return newObj._recuresivelyResetEvents()

    def _recuresivelyResetEvents(self):
        # Loop on all attributes and remove Events
        for attrKey, attrVal in self.__dict__.items():
            try:
                if isinstance(attrVal, Event):
                    self.__dict__[attrKey] = None
                else:
                    self.__dict__[attrKey] = attrVal._recuresivelyResetEvents()
            except:
                # newObj.__dict__[attrKey] is a base type instance not an object
                pass

        return self

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self.setName(name)

    @API.loggedViaAPI
    def setName(self, name):
        self._name = name
        self.nameChangedSignal.emit(self._name)

    @property
    def patient(self):
        return self._patient

    @patient.setter
    def patient(self, patient):
        self.setPatient(patient)

    @API.loggedViaAPI
    def setPatient(self, patient):
        if patient == self._patient:
            return

        self._patient = patient

        if not(self._patient is None):
            self._patient.appendPatienData(self)

    def getType(self):
        return self.__class__.__name__


class EventTestCase(unittest.TestCase):
    class testObj(PatientData):
        def __init__(self):
            super().__init__()

            self.field1 = 'a string'
            self.field2 = Event()
            self.field3 = copy.deepcopy(self)

    def testDeepCopyWithoutEvent(self):
        obj = self.testObj()

        newObj = obj.deepCopyWithoutEvent()
        self.assertIsNone(newObj.field2)
        self.assertIsNone(newObj.field3.field2)
        self.assertEqual(newObj.field1, 'a string')
        self.assertEqual(newObj.field3.field1, 'a string')

