import numpy as np

import opentps_core
from opentps_core.opentps.core.data import CTImage
from opentps_core.opentps.core.data import ROIMask
from opentps_core.opentps.core.data import Patient
from opentps_core.opentps.core.IO import mcsquareIO
from opentps_core.opentps.core.IO import readScanner
from opentps_core.opentps.core.Processing.DoseCalculation.doseCalculationConfig import DoseCalculationConfig

patientList = opentps_core.patientList

patient = Patient()
patient.name = 'Patient'

patientList.append(patient)


ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)
bdl = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)

ctSize = 100

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
data[30:80, 70:90, 30:80] = True
roi.imageArray = data

opentps_core.run()  # Launch opentps_core
