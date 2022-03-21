import os

import numpy as np

from Core.Data.CTCalibrations.RayStationCalibration.rayStationCTCalibration import RayStationCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.patient import Patient
from Core.IO import mcsquareIO
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.api import API
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam
from Extensions.FLASH.Core.Processing.CEMOptimization import cemObjectives, planObjectives
from Extensions.FLASH.Core.Processing.CEMOptimization.cemOptimizer import CEMOptimizer, CEMDoseCalculator

# openTPS patient list
patientList = API.patientList

# We create a dummy patient for this study
patient = Patient()
patient.name = 'Patient0'

patientList.append(patient)

# Create a CT larger in dim 1 so that it can fully contain the CEF
ct = CTImage()
ctSize = (256, 512, 256)
imageArray = -990.*np.ones(ctSize)
imageArray[:, 400:, :] = 0
ct.imageArray = imageArray
ct.name = 'CT'
ct.patient = patient
ct.orgin = (0, 0, 0)
ct.spacing = (1, 1, 1)

# Target ROI
roi = ROIMask.fromImage3D(ct)
roiArray = np.zeros(roi.imageArray.shape)
roiArray[80:130, 420:470, 80:130] = 1
roi.imageArray = roiArray.astype(bool)
roi.name = 'TV'
roi.patient = patient

# Change this to your own paths
calibration = RayStationCTCalibration(fromFiles=('/home/sylvain/Documents/Reggui/flashTPS/parameters/calibration_trento_cef.txt',
                                       '/home/sylvain/Documents/Reggui/flashTPS/parameters/materials_cef.txt'))
bdl = mcsquareIO.readBDL(os.path.join(str('/home/sylvain/Documents/Reggui/flashTPS/parameters/BDL_default_RS_Leuven_4_5_5.txt')))

# Create a plan with a single energy layer since this is a FLASH plan
plan = RTPlan()
beam = CEMBeam()
beam.isocenterPosition = roi.centerOfMass
beam.gantryAngle = 0.
beam.cemToIsocenter = 50
layer = PlanIonLayer(nominalEnergy=220.)
beam.appendLayer(layer)
plan.appendBeam(beam)

# A single optimizer for both plan an CEM
cemOptimizer = CEMOptimizer()
cemOptimizer.maxIterations = 25
cemOptimizer.spotSpacing = 4
cemOptimizer.targetMask = roi
cemOptimizer.absTol = 0.2
cemOptimizer.ctCalibration = calibration

# This is a dose calculator that will cache results and only recompute them if CEM or plan has changed
doseCalculator = CEMDoseCalculator()
doseCalculator.beamModel = bdl
doseCalculator.nbPrimaries = 1e4
doseCalculator.ctCalibration = calibration
doseCalculator.plan = plan
doseCalculator.roi = roi
doseCalculator.ct = ct

# These are our objectives
objectifMin = cemObjectives.DoseMinObjective(roi, 10, doseCalculator)
objectifMax = cemObjectives.DoseMaxObjective(roi, 10.2, doseCalculator)

cemOptimizer.appendObjective(objectifMin, weight=1.)
cemOptimizer.appendObjective(objectifMax, weight=1.)

# Let's optimize the plan and the CEM!
cemOptimizer.run(plan, ct)

cem = plan.beams[0].cem

# Update CT with CEM
cemROI = cem.computeROI(ct, beam)
ctArray = ct.imageArray
ctArray[cemROI.imageArray.astype(bool)] = calibration.convertHU2RSP(cem.rsp, energy=100.)
ct.imageArray = ctArray

# Final dose computation
doseCalculator = MCsquareDoseCalculator()
doseCalculator.beamModel = bdl
doseCalculator.nbPrimaries = 2e7
doseCalculator.ctCalibration = calibration

doseImage = doseCalculator.computeDose(ct, plan)
doseImage.patient = patient
doseImage.name = 'Final dose'
