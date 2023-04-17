
__all__ = ['PatientData']


import copy
import unittest

import numpy as np
import pydicom

from opentps.core import Event


class PatientData:
    _staticVars = {"deepCopyingExceptNdArray": False}

    def __init__(self, name='', seriesInstanceUID='', patient=None):

        self.nameChangedSignal = Event(str)
        # self.setEvents()

        self._name = name
        self._patient = None

        if seriesInstanceUID:
            self.seriesInstanceUID = seriesInstanceUID
        else:
            self.seriesInstanceUID = pydicom.uid.generate_uid()

        self.setPatient(patient)

    def __deepcopy__(self, memodict={}):
        # We don't copy patient
        patient = self._patient
        self._patient = None

        cls = self.__class__
        result = cls.__new__(cls)
        memodict[id(self)] = result
        for attrKey, attrVal in self.__dict__.items():
            # Do not deep copy numpy array
            if self._staticVars["deepCopyingExceptNdArray"] and isinstance(attrVal, np.ndarray):
                setattr(result, attrKey, attrVal)
            else:
                setattr(result, attrKey, copy.deepcopy(attrVal, memodict))

        self._patient = patient
        #result.patient = patient
        return result

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name:str):
        self.setName(name)

    def setName(self, name:str):
        self._name = name
        self.nameChangedSignal.emit(self._name)

    #Cannot add type hint for Patient because this creates a circular import
    @property
    def patient(self):
        return self._patient

    @patient.setter
    def patient(self, patient):
        self.setPatient(patient)

    def setPatient(self, patient):
        if patient == self._patient:
            return

        self._patient = patient

        if not(self._patient is None):
            self._patient.appendPatientData(self)

    def getTypeAsString(self) -> str:
        return self.__class__.__name__


class EventTestCase(unittest.TestCase):
    def testProperties(self):
        name = 'name'

        obj = PatientData()
        obj.name = name

        from opentps.core.data import Patient
        patient = Patient()
        obj.patient = patient

        self.assertEqual(obj.name, name)
        self.assertEqual(obj.patient, patient)

        name = 'name2'
        patient = Patient()

        obj.setName(name)
        obj.setPatient(patient)

        self.assertEqual(obj.name, name)
        self.assertEqual(obj.patient, patient)
