import numpy as np

from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.patient import Patient
from Core.Data.patientList import PatientList
from Core.IO import mcsquareIO
from Core.IO.scannerReader import readScanner
from Core.api import API
from main import main
from programSettings import ProgramSettings

patientList = PatientList()

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

API.patientList = patientList # Give API to opentps
main()  # Launch opentps
