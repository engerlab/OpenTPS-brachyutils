import os
import numpy as np

from Core.Data.CTCalibrations.RayStationCalibration.rayStationCTCalibration import RayStationCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
import Core.IO.mcsquareIO as mcsquareIO
from Core.Data.patient import Patient
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.api import API
from Extensions.FLASH.Core.Processing.DoseCalculation.fluenceBasedMCsquareDoseCalculator import \
    FluenceBasedMCsquareDoseCalculator

patientList = API.patientList

patient = Patient()
patient.name = 'Patient'
patientList.append(patient)

ct = CTImage()
ct.name = 'CT'
ct.patient = patient
ct.origin = (0, 0, 0)
ct.spacing = (1, 1, 1)
ctSize = (256, 256, 256)

imageArray = -1024.*np.ones(ctSize)
imageArray[:, 150:, :] = 0
ct.imageArray = imageArray

calibration = RayStationCTCalibration(fromFiles=('/home/sylvain/Documents/Reggui/flashTPS/parameters/calibration_trento_cef.txt',
                                       '/home/sylvain/Documents/Reggui/flashTPS/parameters/materials_cef.txt'))
bdl = mcsquareIO.readBDL(os.path.join(str('/home/sylvain/Documents/Reggui/flashTPS/parameters/BDL_default_RS_Leuven_4_5_5.txt')))


plan = RTPlan()
beam = PlanIonBeam()
beam.isocenterPosition = (100., 150., 100.)
beam.gantryAngle = 0.
layer = PlanIonLayer(nominalEnergy=100.)
layer.appendSpot(0., 0., 10.)
beam.appendLayer(layer)
plan.appendBeam(beam)

doseCalculator = FluenceBasedMCsquareDoseCalculator()
doseCalculatorNormal = MCsquareDoseCalculator()

doseCalculator.beamModel = bdl
doseCalculator.nbPrimaries = 1e4
doseCalculator.ctCalibration = calibration

doseCalculatorNormal.beamModel = bdl
doseCalculatorNormal.nbPrimaries = 2e6
doseCalculatorNormal.ctCalibration = calibration

beamlets = doseCalculator.computeBeamlets(ct, plan)
doseImage = beamlets.toDoseImage()
doseImage.patient = patient

doseImage = doseCalculatorNormal.computeDose(ct, plan)
doseImage.name = 'Dose_normal'
doseImage.patient = patient
