
__all__ = ['PatientList']

import functools
import unittest
from typing import Sequence

from opentps.core.data._patient import Patient
from opentps.core.data._patientData import PatientData
from opentps.core import Event


class PatientList():
    """
    Class representing a list of patients.

    Attributes
    ----------
    patients : list
        list of patients
    """
    def __init__(self):
        self.patientAddedSignal = Event(object)
        self.patientRemovedSignal = Event(object)

        self._patients = []

    def __getitem__(self, index) -> Patient:
        return self._patients[index]

    def __len__(self):
        return len(self._patients)

    @property
    def patients(self) -> Sequence[Patient]:
        # Doing this ensures that the user can't append directly to patients
        return [patient for patient in self._patients]

    def append(self, patient:Patient):
        """
        Append a patient to the list.

        Parameters
        ----------
        patient : Patient
            patient to append
        """
        self._patients.append(patient)
        self.patientAddedSignal.emit(self._patients[-1])

    def getIndex(self, patient:Patient) -> int:
        """
        Get the index of a patient in the list.

        Parameters
        ----------
        patient : Patient
            patient to get the index of

        Returns
        --------
        int
            index of the patient
        """
        return self._patients.index(patient)

    def getIndexFromPatientID(self, patientID:str) -> int:
        """
        Get the index of a patient in the list based on the patient ID.

        Parameters
        ----------
        patientID : str
            patient ID to get the index of

        Returns
        --------
        int
            index of the patient
        """
        if patientID == "":
            return -1

        index = next((x for x, patient in enumerate(self._patients) if patient.id == patientID), -1)
        return index

    def getIndexFromPatientName(self, patientName:str) -> int:
        """
        Get the index of a patient in the list based on the patient name.

        Parameters
        ----------
        patientName : str
            patient name to get the index of

        Returns
        --------
        int
            index of the patient
        """
        if patientName == "":
            return -1

        index = next((x for x, patient in enumerate(self._patients) if patient.name == patientName), -1)
        return index

    def getPatientByData(self, patientData:PatientData) -> Patient:
        """
        Get the patient that contains a specific patient data.

        Parameters
        ----------
        patientData : PatientData
            patient data to search for

        Returns
        --------
        Patient
            patient that contains the patient data
        """
        for patient in self._patients:
            if patient.hasPatientData(patientData):
                return patient

        return None

    def getPatientByPatientId(self, id:str) -> Patient:
        """
        Get the patient with a specific patient ID.

        Parameters
        ----------
        id : str
            patient ID to search for
        Returns
        --------
        Patient
            patient with the patient ID
        """
        for i, patient in enumerate(self._patients):
            if patient.id==id:
                return patient
        raise Exception('Patient not found')

    def remove(self, patient:Patient):
        """
        Remove a patient from the list.

        Parameters
        ----------
        patient : Patient
            patient to remove
        """
        self._patients.remove(patient)
        self.patientRemovedSignal.emit(patient)

    def dumpableCopy(self):
        """
        Get a dumpable copy of the patient list.

        Returns
        --------
        PatientList
            dumpable copy of the patient list

        """

        dumpablePatientListCopy = PatientList()
        for patient in self._patients:
            dumpablePatientListCopy._patients.append(patient.dumpableCopy())

        return dumpablePatientListCopy()

class EventTestCase(unittest.TestCase):
    def testPropertiesAndAccessMethods(self):
        from opentps.core.data import Patient
        patient = Patient()

        obj = PatientList()
        obj.patientAddedSignal.connect(functools.partial(self._assertPatientAdded, patient))
        obj.patientRemovedSignal.connect(functools.partial(self._assertPatientRemoved, patient))

        obj.append(patient)
        self.assertEqual(obj.patients[0], patient)
        self.assertEqual(obj.getIndex(patient), 0)

        obj.remove(patient)
        with self.assertRaises(ValueError) as cm:
            obj.getIndex(patient)
        self.assertEqual(len(obj.patients), 0)

    def _assertPatientAdded(self, refPatient, patient):
        self.assertEqual(refPatient, patient)

    def _assertPatientRemoved(self, refPatient, patient):
        self.assertEqual(refPatient, patient)
