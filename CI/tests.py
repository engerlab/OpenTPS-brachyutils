
import numpy as np

from opentps.core.data import PatientList
from opentps.core.data.images import CTImage
from opentps.core.data.images import ROIMask
from opentps.core.data import Patient
from opentps.core.io import mcsquareIO, scannerReader
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig


print('TEST')

patient = Patient()
patient.name = 'Patient'

patientList = PatientList()
patientList.append(patient)


ctCalibration = scannerReader.readScanner(DoseCalculationConfig().scannerFolder)
bdl = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)

ctSize = 150

ct = CTImage()
ct.name = 'CT'
ct.patient = patient

huAir = -1024.
huWater = ctCalibration.convertRSP2HU(1.)
data = huAir * np.ones((ctSize, ctSize, ctSize))
data[:, 50:, :] = huWater
ct.imageArray = data

roi = ROIMask()
roi.patient = patient
roi.name = 'TV'
roi.color = (255, 0, 0) # red
data = np.zeros((ctSize, ctSize, ctSize)).astype(bool)
data[100:120, 100:120, 100:120] = True
roi.imageArray = data
