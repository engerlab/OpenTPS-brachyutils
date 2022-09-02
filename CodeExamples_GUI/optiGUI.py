import numpy as np

import opentps
from Core.Data.Images import CTImage
from Core.Data.Images import ROIMask
from Core.Data import Patient
from Core.Data import PatientList
from Core.IO import mcsquareIO
from Core.IO.scannerReader import readScanner
from programSettings import ProgramSettings

patientList = opentps.patientList

ctCalibration = readScanner(ProgramSettings().scannerFolder)
bdl = mcsquareIO.readBDL(ProgramSettings().bdlFile)

patient = Patient()
patient.name = 'Patient'

patientList.append(patient)

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

opentps.run()  # Launch opentps
