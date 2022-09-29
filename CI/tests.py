
import numpy as np

from opentps.core.data import PatientList
from opentps.core.data.images import CTImage
from opentps.core.data.images import ROIMask
from opentps.core.data import Patient
from opentps.core.io import mcsquareIO, scannerReader
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.examples.registration import exampleMorphons


print('TEST')

patient = Patient()
patient.name = 'Patient'

patientList = PatientList()
patientList.append(patient)

exampleMorphons.run()
