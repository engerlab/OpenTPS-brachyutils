import copy
import unittest

import numpy as np
import pydicom

from Core.Data.patientInfo import PatientInfo
from Core.api import API
from Core.event import Event


class PatientData:
    _staticVars = {"deepCopyingExceptNdArray": False}

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

    def __deepcopy__(self, memodict={}):
        cls = self.__class__
        result = cls.__new__(cls)
        memodict[id(self)] = result
        for attrKey, attrVal in self.__dict__.items():
            # Do not deep copy numpy array
            if self._staticVars["deepCopyingExceptNdArray"] and isinstance(attrVal, np.ndarray):
                setattr(result, attrKey, attrVal)
            else:
                setattr(result, attrKey, copy.deepcopy(attrVal, memodict))
        return result

    def deepCopyWithoutEventExceptNdArray(self):
        self._staticVars["deepCopyingExceptNdArray"] = True
        try:
            newObj = copy.deepcopy(self)
        except Exception as e:
            self._staticVars["deepCopyingExceptNdArray"] = False
            raise(e)
        self._staticVars["deepCopyingExceptNdArray"] = False

        return newObj._recuresivelyResetEvents()

    def deepCopyWithoutEvent(self):
        newObj = copy.deepcopy(self)
        return newObj._recuresivelyResetEvents()

    def _recuresivelyResetEvents(self, checkedItems = []):
        # Loop on all attributes and remove Events
        for attrKey, attrVal in self.__dict__.items():
            try:
                if isinstance(attrVal, Event):
                    self.__dict__[attrKey] = Event(object)
                elif attrVal not in checkedItems :
                    checkedItems.append(attrVal) # Avoid infinite loop
                    self.__dict__[attrKey] = attrVal._recuresivelyResetEvents(checkedItems=checkedItems)
                else:
                    pass
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

