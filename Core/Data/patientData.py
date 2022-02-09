import copy
import unittest

import numpy as np
import pydicom

from Core.Data.patientInfo import PatientInfo
from Core.api import API
from Core.event import Event


class PatientData:
    _staticVars = {"deepCopyingExceptNdArray": False}

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
    class TestObjEventParent(PatientData):
        def __init__(self):
            super().__init__()
            self.eventField = Event()
            self.parent = None

    class TestObj(PatientData):
        def __init__(self):
            super().__init__()

            self.stringField = 'a string'
            self.eventField = Event()
            self.selfField = self
            self.objectField = EventTestCase.TestObjEventParent()
            self.objectField.eventField = Event()
            self.objectField.parent = self

            self.eventField.connect(EventTestCase.dummyMethod)
            self.objectField.eventField.connect(EventTestCase.dummyMethod)

    def dummyMethod(self):
        from PyQt5.QtWidgets import QWidget
        QWidget()
        return


    def testDeepCopyWithoutEvent(self):
        obj = self.TestObj()

        newObj = obj.deepCopyWithoutEvent()
        self.assertIsNone(newObj.eventField)
        self.assertIsNone(newObj.objectField.eventField)
        self.assertIsNone(newObj.selfField.eventField)
        self.assertEqual(newObj.stringField, obj.stringField)
        self.assertEqual(newObj.selfField.stringField, obj.stringField)

    def testShallowCopyWithoutEvent(self):
        obj = self.TestObj()

        newObj = obj.shallowCopyWithoutEvent()
        self.assertIsNone(newObj.eventField)
        self.assertIsNone(newObj.objectField.eventField)
        self.assertIsNone(newObj.selfField.eventField)
        self.assertEqual(newObj.stringField, obj.stringField)
        self.assertEqual(newObj.selfField.stringField, obj.stringField)
        self.assertEqual(obj, newObj.selfField)
        self.assertEqual(obj, newObj.objectField.parent)

