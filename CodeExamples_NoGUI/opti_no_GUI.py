import os
import numpy as np
import scipy.sparse as sp
from matplotlib import pyplot as plt

from Core.Data.patientList import PatientList
from Core.Data.Images.doseImage import DoseImage
from Core.Data.dvh import DVH
from Core.IO import mcsquareIO
from Core.IO.dataLoader import loadAllData, listAllFiles
from Core.IO.dicomReader import readDicomCT, readDicomPlan
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareCTCalibration import MCsquareCTCalibration
from Core.Processing.PlanOptimization.planOptimization import IMPTPlanOptimizer
from Core.IO.serializedObjectIO import loadRTPlan, saveRTPlan, loadBeamlets, saveBeamlets
from Core.Data.Plan.objectivesList import ObjectivesList
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.Plan.planStructure import PlanStructure


# User config:
ctImagePath = "/home/sophie/Documents/Protontherapy/OpenTPS/arc_dev/opentps/data/Plan_IMPT_patient1"
output_path = os.path.join(ctImagePath, "OpenTPS")
# dataStructPath = os.path.join(ctImagePath, "reggui_phantom_5mm_rtstruct.dcm")

# Create output folder
if not os.path.isdir(output_path):
    os.mkdir(output_path)

# Load patient data

# filesList = listAllFiles(ctImagePath)
# image1 = readDicomCT(filesList['Dicom'])
dataList = loadAllData(ctImagePath, maxDepth=0)
print(dataList)
ct = dataList[5]
contours = dataList[4]
# structData = loadAllData(dataStructPath)[0]
print('Available ROIs')
contours.print_ROINames()

# Configure MCsquare
MCSquarePath = '../Core/Processing/DoseCalculation/MCsquare/'
doseCalculator = MCsquareDoseCalculator()
beamModel = mcsquareIO.readBDL(os.path.join(MCSquarePath, 'BDL', 'UMCG_P1_v2_RangeShifter.txt'))
doseCalculator.beamModel = beamModel
doseCalculator.nbPrimaries = 5e4
scannerPath = os.path.join(MCSquarePath, 'Scanners', 'UCL_Toshiba')
calibration = MCsquareCTCalibration(fromFiles=(os.path.join(scannerPath, 'HU_Density_Conversion.txt'),
                                               os.path.join(scannerPath, 'HU_Material_Conversion.txt'),
                                               os.path.join(MCSquarePath, 'Materials')))
doseCalculator.ctCalibration = calibration

# ROIs
target = contours.getContourByName('CTV')
targetMask = target.getBinaryMask(origin=ct.origin, gridSize=ct.gridSize, spacing=ct.spacing)
opticChiasm = contours.getContourByName('Optic Chiasm')
brainStem = contours.getContourByName('Brain Stem')



beamNames = ["Beam1", "Beam2"]
gantryAngles = [90., 270.]
couchAngles = [0., 0.]

# Load / Generate new plan
plan_file = os.path.join(output_path, "NewPlan.tps")

if os.path.isfile(plan_file):
    print('test')
    plan = loadRTPlan(plan_file)
else:
    print('test 2 ')
    planInit = PlanStructure()
    planInit.ct = ct
    planInit.targetMask = targetMask
    planInit.gantryAngles = gantryAngles
    planInit.beamNames = beamNames
    planInit.couchAngles = couchAngles
    planInit.calibration = calibration
    plan = planInit.createPlanStructure()  # Spot placement
    plan.PlanName = "NewPlan"
    beamlets = doseCalculator.computeBeamlets(ct,plan,roi=targetMask)
    outputBeamletFile = os.path.join(output_path, "BeamletMatrix_" + plan.SeriesInstanceUID + ".blm")
    plan.save(plan_file)

quit()
# Load openTPS plan
# plan = dataList[3]

# Load Dicom plan
# plan_path = '../data/.dcm'
# plan = readDicomPlan(plan_path)

# Load Beamlets
beamletPath = os.path.join(output_path,"")
plan.beamlets = loadBeamlets(beamletPath)

# optimization objectives
plan.objectives.setTarget(target.ROIName, 60.0)
plan.objectives.fidObjList = []
plan.objectives.addFidObjective(target.ROIName, "Dmax", "<", 60.0, 5.0)
plan.objectives.addFidObjective(target.ROIName, "Dmin", ">", 60.0, 5.0)

# Compute pre-optimization dose
dose_vector = plan.beamlets.Compute_dose_from_beamlets()
dose = RTdose().Initialize_from_beamlet_dose(plan.PlanName, plan.beamlets, dose_vector, ct)
dose = plan.beamlets.toDoseImage()

# Compute DVH
target_DVH = DVH(Target, doseImage)
chiasm_DVH = DVH(Optic_Chiasm, doseImage)
stem_DVH = DVH(Brain_Stem, doseImage)

# Find target center for display
maskY, maskX, maskZ = np.nonzero(TargetMask)
targetCenter = [np.mean(maskX), np.mean(maskY), np.mean(maskZ)]
Z_coord = int(targetCenter[2])

# Display dose
plt.figure(figsize=(10, 10))
plt.subplot(2, 2, 1)
plt.imshow(ct.imageArray[:, :, Z_coord], cmap='gray')
#plt.imshow(Target.ContourMask[:, :, Z_coord], alpha=.2, cmap='binary')  # PTV
#plt.imshow(dose.Image[:, :, Z_coord], cmap='jet', alpha=.2)
plt.title("Pre-optimization dose")
plt.subplot(2, 2, 2)
plt.plot(target_DVH.dose, target_DVH.volume, label=target_DVH.ROIName)
plt.plot(chiasm_DVH.dose, chiasm_DVH.volume, label=chiasm_DVH.ROIName)
plt.plot(stem_DVH.dose, stem_DVH.volume, label=stem_DVH.ROIName)
plt.title("Pre-optimization DVH")

# Optimize treatment plan
solver = IMPTPlanOptimizer(method='Scipy-BFGS', plan=plan, contours=contours)
w, dose_vector, ps = solver.optimize()
# dose = RTdose().Initialize_from_beamlet_dose(plan.PlanName, plan.beamlets, dose_vector, ct)
plan_file = os.path.join(output_path, "NewPlan_optimized.tps")
plan.save(plan_file)

# MCsquare simulation
# doseImage = doseCalculator.computeDose(ct, plan3)

# Compute DVH
target_DVH = DVH(Target, doseImage)
chiasm_DVH = DVH(Optic_Chiasm, doseImage)
stem_DVH = DVH(Brain_Stem, doseImage)

print('D95 = ' + str(target_DVH.D95) + ' Gy')

# Display dose
plt.subplot(2, 2, 3)
plt.imshow(ct.imageArray[:, :, Z_coord], cmap='gray')
# plt.imshow(Target.ContourMask[:, :, Z_coord], alpha=.2, cmap='binary')  # PTV
# plt.imshow(dose.Image[:, :, Z_coord], cmap='jet', alpha=.2)
plt.title("Optimized dose")
plt.subplot(2, 2, 4)
plt.plot(target_DVH.dose, target_DVH.volume, label=target_DVH.ROIName)
plt.plot(chiasm_DVH.dose, chiasm_DVH.volume, label=chiasm_DVH.ROIName)
plt.plot(stem_DVH.dose, stem_DVH.volume, label=stem_DVH.ROIName)
plt.title("Optimized DVH")
plt.show()
