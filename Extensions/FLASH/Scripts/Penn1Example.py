import copy
import os

import numpy as np

from Core.Data.CTCalibrations.RayStationCalibration.rayStationCTCalibration import RayStationCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.rtStruct import RTStruct
from Core.IO import mcsquareIO
from Core.IO.dataLoader import loadData
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing.crop3D import crop3DDataAroundBox
from Core.Processing.ImageProcessing.imageTransform3D import ImageTransform3D
from Core.api import API
from Extensions.FLASH.Core.Data.cemBeam import CEMBeam
from Extensions.FLASH.Core.Processing.CEMOptimization import cemObjectives, planObjectives
from Extensions.FLASH.Core.Processing.CEMOptimization.cemOptimizer import CEMOptimizer, CEMDoseCalculator


# Change this to your own paths
loadData(API.patientList,['/home/sylvain/Documents/PT_1'])

ctCalibration = RayStationCTCalibration(fromFiles=('/home/sylvain/Documents/Reggui/flashTPS/parameters/calibration_trento_cef.txt',
                                       '/home/sylvain/Documents/Reggui/flashTPS/parameters/materials_cef.txt'))
bdl = mcsquareIO.readBDL(os.path.join(str('/home/sylvain/Documents/Reggui/flashTPS/parameters/BDL_default_RS_Leuven_4_5_5.txt')))


patientList = API.patientList
patient = patientList[0]

ct:CTImage = patient.getPatientDataOfType(CTImage)[0]
rtStruct:RTStruct = patient.getPatientDataOfType(RTStruct)[0]

targetContour = rtStruct.getContourByName('FLASHTarget')
targetROI = targetContour.getBinaryMask(origin=ct.origin, gridSize=ct.gridSize, spacing=ct.spacing)


# Crop CT
ct2 = copy.deepcopy(ct)
crop3DDataAroundBox(ct2, [[-30, 100], [-70, 35], [-670, -570]])
ct2.patient = patient
ct = ct2

targetROI2 = copy.deepcopy(targetROI)
crop3DDataAroundBox(targetROI2, [[-30, 100], [-70, 35], [-670, -570]])
targetROI2.patient = patient
targetROI = targetROI2

# Create a plan with a single energy layer since this is a FLASH plan
plan = RTPlan()
beam = CEMBeam()
beam.isocenterPosition = targetROI.centerOfMass
beam.gantryAngle = 45.
beam.cemToIsocenter = 80. # Distance between CEM and isocenter
layer = PlanIonLayer(nominalEnergy=180.)
beam.appendLayer(layer)
plan.appendBeam(beam)

# Pad CT and targetROI so that both can fully contain the CEM
ctBEV = ImageTransform3D.dicomToIECGantry(ct, beam, fillValue=-1024.)
targetROIBEV = ImageTransform3D.dicomToIECGantry(targetROI, beam, fillValue=-0.)

padLength = int(150./ctBEV.spacing[2])
newOrigin = np.array(ctBEV.origin)
newOrigin[2] = newOrigin[2] - padLength*ctBEV.spacing[2]
newArray = -1024*np.ones((ctBEV.gridSize[0], ctBEV.gridSize[1], ctBEV.gridSize[2]+padLength))
newArray[:, :, padLength:] = ctBEV.imageArray
ctBEV.imageArray = newArray
ctBEV.origin = newOrigin

newArray = np.zeros((targetROIBEV.gridSize[0], targetROIBEV.gridSize[1], targetROIBEV.gridSize[2]+padLength))
newArray[:, :, padLength:] = targetROIBEV.imageArray
targetROIBEV.imageArray = newArray
targetROIBEV.origin = newOrigin

ct = ImageTransform3D.iecGantryToDicom(ctBEV, beam, fillValue=-1024.)
ct.patient = patient
targetROI = ImageTransform3D.iecGantryToDicom(targetROIBEV, beam, fillValue=0)
targetROI.patient = patient

crop3DDataAroundBox(ct,[[-30, 250], [-250, 35], [-670, -570]], [0,0,0])
crop3DDataAroundBox(targetROI,[[-30, 250], [-250, 35], [-670, -570]], [0,0,0])

# OARs are defined around the TV
oarAndTVROI = copy.deepcopy(targetROI)
oarAndTVROI.dilate(10)

oarROI = copy.deepcopy(targetROI)
oarROI.imageArray = np.logical_xor(oarAndTVROI.imageArray.astype(bool), targetROI.imageArray.astype(bool))

# A single optimizer for both plan an CEM
cemOptimizer = CEMOptimizer()
cemOptimizer.maxIterations = 25
cemOptimizer.spotSpacing = 5
cemOptimizer.targetMask = targetROI
cemOptimizer.absTol = 1
cemOptimizer.ctCalibration = ctCalibration

# This is a dose calculator that will cache results and only recompute them if CEM or plan has changed
doseCalculator = CEMDoseCalculator()
doseCalculator.beamModel = bdl
doseCalculator.nbPrimaries = 1e4
doseCalculator.ctCalibration = ctCalibration
doseCalculator.plan = plan
doseCalculator.roi = oarAndTVROI
doseCalculator.ct = ct


# These are our objectives
objectifMin = cemObjectives.DoseMinObjective(targetROI, 40, doseCalculator)
objectifMax = cemObjectives.DoseMaxObjective(targetROI, 40.2, doseCalculator)
objectifMax2 = cemObjectives.DoseMaxObjective(oarROI, 20, doseCalculator)


cemOptimizer.appendObjective(objectifMin, weight=1.)
cemOptimizer.appendObjective(objectifMax, weight=1.)
cemOptimizer.appendObjective(objectifMax2, weight=0.5)



# Let's optimize the plan and the CEM!
cemOptimizer.run(plan, ct)


# Update CT with CEM
cem = plan.beams[0].cem
cemROI = cem.computeROI(ct, beam)
ctArray = ct.imageArray
ctArray[cemROI.imageArray.astype(bool)] = ctCalibration.convertHU2RSP(cem.rsp, energy=70.)
ct.imageArray = ctArray

# Final dose computation
doseCalculator = MCsquareDoseCalculator()
doseCalculator.beamModel = bdl
doseCalculator.nbPrimaries = 1e7
doseCalculator.ctCalibration = ctCalibration

doseImage = doseCalculator.computeDose(ct, plan)
doseImage.patient = patient
doseImage.name = 'Final dose'
