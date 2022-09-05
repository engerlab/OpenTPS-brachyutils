import numpy as np

import opentps
from Core.Data.Images import CTImage
from Core.Data.Images import ROIMask
from Core.Data import Patient
from Core.IO import mcsquareIO
from Core.IO.scannerReader import readScanner
from Core.Processing.DoseCalculation.doseCalculationConfig import DoseCalculationConfig
from Core.Processing.ImageProcessing import resampler3D

patientList = opentps.patientList

ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)
bdl = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)

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

ct2 = CTImage.fromImage3D(ct)
ct2.spacing = np.array([0.8, 0.8, 0.8])
ct2.imageArray = huAir * np.ones((ctSize-3, ctSize-3, ctSize-3))
resampler3D.resampleImage3DOnImage3D(roi, ct2, inPlace=True, fillValue=0)

opentps.run()  # Launch opentps
