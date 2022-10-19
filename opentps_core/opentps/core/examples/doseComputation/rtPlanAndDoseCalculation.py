import os

from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.io.scannerReader import readScanner
from opentps.core.io.serializedObjectIO import loadRTPlan, saveRTPlan
from opentps.core.io.dicomIO import readDicomPlan
from opentps.core.io.dataLoader import readData
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareCTCalibration import MCsquareCTCalibration
from opentps.core.io import mcsquareIO
from opentps.core.data._dvh import DVH
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.io.mhdIO import exportImageMHD
from opentps.core.data.plan._planIonBeam import PlanIonBeam
from opentps.core.data.plan._planIonLayer import PlanIonLayer
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data._rtStruct import RTStruct

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
plan_path = r"C:\Users\valentin.hamaide\data\ARIES\patient_0\plan_4D_robust.dcm"
plan3 = readDicomPlan(plan_path)


## Dose computation from plan

# Choosing default Scanner and BDL
doseCalculator = MCsquareDoseCalculator()
doseCalculator.ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)
doseCalculator.beamModel = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)
doseCalculator.nbPrimaries = 1e7

# Manually specify Scanner and BDL
# openTPS_path = r'C:\Users\valentin.hamaide\flash_tps\opentps\opentps_core\opentps'
# MCSquarePath = os.path.join(openTPS_path, 'core', 'processing', 'doseCalculation', 'MCsquare')
# doseCalculator = MCsquareDoseCalculator()
# beamModel = mcsquareIO.readBDL(os.path.join(MCSquarePath, 'BDL', 'UMCG_P1_v2_RangeShifter.txt'))
# doseCalculator.beamModel = beamModel
# doseCalculator.nbPrimaries = 1e7
# scannerPath = os.path.join(MCSquarePath, 'Scanners', 'UCL_Toshiba')

# calibration = MCsquareCTCalibration(fromFiles=(os.path.join(scannerPath, 'HU_Density_Conversion.txt'),
#                                                 os.path.join(scannerPath, 'HU_Material_Conversion.txt'),
#                                                 os.path.join(MCSquarePath, 'Materials')))
# doseCalculator.ctCalibration = calibration

ctImagePath = r'C:\Users\valentin.hamaide\data\ARIES\patient_0\MidP_CT'
dataList = readData(ctImagePath, maxDepth=0)
ct = [d for d in dataList if isinstance(d, CTImage)][0]
struct = [d for d in dataList if isinstance(d, RTStruct)][0]

# If we want to crop the CT to the body contour (set everything else to -1024)
contour_name = 'body'
body_contour = struct.getContourByName(contour_name)
doseCalculator.overwriteOutsideROI = body_contour

# MCsquare simulation
doseImage = doseCalculator.computeDose(ct, plan3)

# Export dose
exportImageMHD(r'C:\Users\valentin.hamaide\data\ARIES\patient_0\test_dose.mhd', doseImage)

# DVH
target_name = 'MidP CT GTV'
target_contour = struct.getContourByName(target_name)
dvh = DVH(target_contour, doseImage)
print("D95",dvh._D95)
print("D5",dvh._D5)
print("Dmax",dvh._Dmax)
print("Dmin",dvh._Dmin)
