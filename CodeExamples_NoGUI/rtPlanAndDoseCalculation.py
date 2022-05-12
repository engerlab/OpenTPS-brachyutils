import sys

sys.path.append('..')

from Core.Data.dvh import DVH
import os
from Core.IO.dataLoader import listAllFiles, loadAllData
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareCTCalibration import MCsquareCTCalibration
from Core.IO import mcsquareIO
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.IO.mhdReadWrite import exportImageMHD
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.IO.serializedObjectIO import loadRTPlan, saveRTPlan
from Core.IO.dicomReader import readDicomCT, readDicomPlan

# Create plan from scratch
plan = RTPlan()
plan.appendBeam(PlanIonBeam())
plan.appendBeam(PlanIonBeam())
plan.beams[1].gantryAngle = 120.
plan.beams[0].appendLayer(PlanIonLayer(100))
plan.beams[0].appendLayer(PlanIonLayer(90))
plan.beams[1].appendLayer(PlanIonLayer(80))
plan[0].layers[0].appendSpot([-1,0,1], [1,2,3], [0.1,0.2,0.3])
plan[0].layers[1].appendSpot([0,1], [2,3], [0.2,0.3])
plan[1].layers[0].appendSpot(1, 1, 0.5)
# Save plan
saveRTPlan(plan,'test_plan.tps')


# Load plan in OpenTPS format (serialized)
plan2 = loadRTPlan('test_plan.tps')
print(plan2[0].layers[1].spotWeights)
print(plan[0].layers[1].spotWeights)


# Load DICOM plan
plan_path = '/data/vhamaide/liver/patient_0/MidP_CT/Raystation/plan_4D_robust.dcm'
plan3 = readDicomPlan(plan_path)


# Dose computation from plan
openTPS_path = '/home/vhamaide/opentps'
MCSquarePath = os.path.join(openTPS_path, 'Core/Processing/DoseCalculation/MCsquare/')
doseCalculator = MCsquareDoseCalculator()
beamModel = mcsquareIO.readBDL(os.path.join(MCSquarePath, 'BDL', 'UMCG_P1_v2_RangeShifter.txt'))
doseCalculator.beamModel = beamModel
doseCalculator.nbPrimaries = 1e7
scannerPath = os.path.join(MCSquarePath, 'Scanners', 'UCL_Toshiba')

calibration = MCsquareCTCalibration(fromFiles=(os.path.join(scannerPath, 'HU_Density_Conversion.txt'),
                                                os.path.join(scannerPath, 'HU_Material_Conversion.txt'),
                                                os.path.join(MCSquarePath, 'Materials')))
doseCalculator.ctCalibration = calibration

ctImagePath = '/data/vhamaide/liver/patient_0/MidP_CT/'
dataList = loadAllData(ctImagePath, maxDepth=0)
ct = dataList[1]
struct = dataList[0]

# If we want to crop the CT to the body contour (set everything else to -1024)
contour_name = 'body'
body_contour = struct.getContourByName(contour_name)
doseCalculator.overwriteOutsideROI = body_contour

# MCsquare simulation
doseImage = doseCalculator.computeDose(ct, plan3)

# Export dose
exportImageMHD('/data/vhamaide/liver/patient_0/MidP_CT/test_dose.mhd', doseImage)

# DVH
target_name = 'MidP CT GTV'
target_contour = struct.getContourByName(target_name)
dvh = DVH(target_contour, doseImage)
print("D95",dvh._D95)
print("D5",dvh._D5)
print("Dmax",dvh._Dmax)
print("Dmin",dvh._Dmin)
