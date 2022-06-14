import math
import os
import numpy as np
import scipy.sparse as sp
from matplotlib import pyplot as plt
import logging.config
import json
import sys

from Core.Data.patientList import PatientList
from Core.Data.Images.doseImage import DoseImage
from Core.Data.dvh import DVH
from Core.IO import mcsquareIO
from Core.IO.dataLoader import loadAllData, listAllFiles
from Core.IO.dicomIO import readDicomCT, readDicomPlan
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareCTCalibration import MCsquareCTCalibration
from Core.Processing.PlanOptimization.Objectives.doseFidelity import DoseFidelity
from Core.Processing.PlanOptimization.Objectives.norms import NormL1, NormL21
from Core.Processing.PlanOptimization.Objectives.energySequencing import EnergySeq
from Core.Processing.PlanOptimization.Objectives.logBarrier import LogBarrier
from Core.Processing.PlanOptimization.planOptimization import IMPTPlanOptimizer, ARCPTPlanOptimizer
from Core.Processing.PlanOptimization.Acceleration.fistaAccel import FistaBacktracking, FistaAccel
from Core.IO.serializedObjectIO import loadRTPlan, saveRTPlan, loadBeamlets, saveBeamlets
from Core.Data.Plan.objectivesList import ObjectivesList
from Core.Processing.ImageProcessing.imageTransform3D import resampleOn
from Core.Processing.PlanOptimization.tools import WeightStructure

from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.Plan.planStructure import PlanStructure

with open('/home/sophie/Documents/Protontherapy/OpenTPS/refactor/opentps/config/logger/logging_config.json',
          'r') as log_fid:
    config_dict = json.load(log_fid)
logging.config.dictConfig(config_dict)
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
ct = dataList[7]
contours = dataList[6]
# structData = loadAllData(dataStructPath)[0]
print('Available ROIs')
contours.print_ROINames()

# Configure MCsquare
MCSquarePath = '../Core/Processing/DoseCalculation/MCsquare/'
doseCalculator = MCsquareDoseCalculator()
beamModel = mcsquareIO.readBDL(os.path.join(MCSquarePath, 'BDL', 'UMCG_P1_v2_RangeShifter.txt'))
doseCalculator.beamModel = beamModel
doseCalculator.nbPrimaries = 5e4
# doseCalculator.independentScoringGrid = True
# doseCalculator.scoringVoxelSpacing = [5.0, 5.0, 5.0]
# doseCalculator.
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
body = contours.getContourByName('BODY')

# rings = target.createROIRings(ct,contours,3,2)

beamNames = ["Beam1", "Beam2"]
gantryAngles = [0., 45.]
couchAngles = [0., 0.]

# Load / Generate new plan
plan_file = os.path.join(output_path, "testRefactorPlan.tps")

'''if os.path.isfile(plan_file):
    plan = loadRTPlan(plan_file)
    print('plan loaded')
    beamletPath = os.path.join(output_path,
                               "BeamletMatrix_1.2.826.0.1.3680043.8.498.69745754105946645553673858433070834612.1.blm")
    plan.beamlets = loadBeamlets(beamletPath)
    print('beamlets loaded')
else:
    planInit = PlanStructure()
    planInit.ct = ct
    planInit.targetMask = targetMask
    planInit.gantryAngles = gantryAngles
    planInit.beamNames = beamNames
    planInit.couchAngles = couchAngles
    planInit.calibration = calibration
    planInit.spotSpacing = 6.0
    planInit.layerSpacing = 4.0
    planInit.targetMargin = 6.0
    plan = planInit.createPlan()  # Spot placement
    plan.PlanName = "NewPlan"
    print(plan.numberOfSpots)
    beamlets = doseCalculator.computeBeamlets(ct, plan, roi=targetMask)
    outputBeamletFile = os.path.join(output_path, "BeamletMatrix_" + plan.seriesInstanceUID + ".blm")
    saveBeamlets(beamlets, outputBeamletFile)
    saveRTPlan(plan, plan_file)
    plan.beamlets = beamlets'''

# Load openTPS plan
# plan = dataList[3]
# Load Dicom plan
plan = dataList[1]
# Load Beamlets
beamletPath = os.path.join(output_path, "beamlet_IMPT_test.blm")
# beamletPath = os.path.join(output_path, "beamlet_arc_test.blm")
plan.beamlets = loadBeamlets(beamletPath)

# optimization objectives
plan.objectives = ObjectivesList()
plan.objectives.setTarget(target.name, 65.0)
plan.objectives.fidObjList = []
plan.objectives.addFidObjective(target.name, "Dmax", "<", 65.0, 1.)
plan.objectives.addFidObjective(target.name, "Dmin", ">", 65.0, 1.0)
# plan.objectives.addFidObjective(body.name, "Dmax", "<", 65.0, 0.1)
# plan.objectives.addFidObjective(opticChiasm.name, "Dmax", "<", 60.0, 0.1)
# plan.objectives.addFidObjective(opticChiasm.name, "Dmean", "<", 50.0, 0.1)
# plan.objectives.addFidObjective(brainStem.name, "Dmax", "<", 55.0, 0.1)
# plan.objectives.addFidObjective(brainStem.name, "Dmean", "<", 8.5, 0.1)
# plan.objectives.addFidObjective(rings[0].name, "Dmax", "<", 65.0, 1.0)
# plan.objectives.addFidObjective(rings[1].name, "Dmax", "<", 55.0, 1.0)
# plan.objectives.addFidObjective(rings[2].name, "Dmax", "<", 45.0, 1.0)
# scoring_spacing = np.array([5, 5, 5])
#scoring_spacing = np.array([2, 2, 2])
#scoring_grid_size = [int(math.floor(i / j * k)) for i, j, k in zip(ct.gridSize, scoring_spacing, ct.spacing)]
#plan.objectives.initializeContours(contours, ct, scoring_grid_size, scoring_spacing)
#plan.objectives.initializeContours(contours, ct, ct.gridSize, ct.spacing)
# Objective functions
objectiveFunction = DoseFidelity(plan.objectives.fidObjList, plan.beamlets.toSparseMatrix(), xSquare=False)
print('pre init')
#objectiveFunction = DoseFidelity(plan.objectives.fidObjList, plan.beamlets.toSparseMatrix(), formatArray=64)
print('fidelity init done')
spotSparsity = NormL1(lambda_=1)
energySeq = EnergySeq(plan, gamma=0.1)
# logBarrier = LogBarrier(plan, beta=0.1)
layerSparsity = NormL21(plan, lambda_=1, scaleReg="summu")

# Acceleration
accel = FistaBacktracking()
# accel = FistaAccel()
# Solvers
# Optimize treatment plan
# solver = IMPTPlanOptimizer(method='LP', plan=plan, contours=contours, functions=[])
# solver = ARCPTPlanOptimizer(method='MIP', plan=plan, contours=contours, functions=[], max_switch_ups=5, time_limit=600)
'''solver = IMPTPlanOptimizer(method='FISTA',
                           plan=plan,
                           functions=[objectiveFunction],
                           step=1,
                           accel=accel,
                           maxit=100)'''
'''solver = IMPTPlanOptimizer(method='Scipy-LBFGS', plan=plan, functions=[objectiveFunction], maxit=100)
solver.xSquared = False
w, doseImage, ps = solver.optimize()
with open('test_weights.npy', 'wb') as f:
    np.save(f, w)
struct = WeightStructure(plan)
irradTime, ups, downs = struct.computeIrradiationTime(w)
layerSparsityPercentage = struct.computeELSparsity(w, 1)
print("Irradiation time = {}, Ups = {}, Downs = {}".format(irradTime, ups, downs))
print("EL sparsity = {} %".format(layerSparsityPercentage))'''

plan_filepath = os.path.join(output_path, "NewPlan_optimized.tps")
# saveRTPlan(plan, plan_filepath)

# MCsquare simulation
# doseImage = doseCalculator.computeDose(ct, plan)
# doseImage = plan.beamlets.toDoseImage()

# MCsquare beamlet free optimization
doseCalculator.nbPrimaries = 1e7
doseImage = doseCalculator.optimizeBeamletFree(ct, plan, [targetMask])

# Compute DVH
target_DVH = DVH(ct, target, doseImage)
chiasm_DVH = DVH(ct, opticChiasm, doseImage)
stem_DVH = DVH(ct, brainStem, doseImage)

print('D95 = ' + str(target_DVH.D95) + ' Gy')
print('D5 = ' + str(target_DVH.D5) + ' Gy')
print('D5 - D95 =  {} Gy'.format(target_DVH.D5 - target_DVH.D95))

# center of mass
COM_coord = targetMask.centerOfMass
COM_index = targetMask.getVoxelIndexFromPosition(COM_coord)
Z_coord = COM_index[2]

img_ct = ct.imageArray[:, :, Z_coord].transpose(1, 0)
contourTargetMask = target.getBinaryContourMask(origin=ct.origin, gridSize=ct.gridSize, spacing=ct.spacing)
img_mask = contourTargetMask.imageArray[:, :, Z_coord].transpose(1, 0)
img_dose = resampleOn(doseImage, ct)
img_dose = img_dose.imageArray[:, :, Z_coord].transpose(1, 0)

# Display dose
fig, ax = plt.subplots(1, 2, figsize=(12, 5))
ax[0].axes.get_xaxis().set_visible(False)
ax[0].axes.get_yaxis().set_visible(False)
ax[0].imshow(img_ct, cmap='gray')
ax[0].imshow(img_mask, alpha=.2, cmap='binary')  # PTV
dose = ax[0].imshow(img_dose, cmap='jet', alpha=.2)
plt.colorbar(dose, ax=ax[0])
ax[1].plot(target_DVH.histogram[0], target_DVH.histogram[1], label=target_DVH.name)
ax[1].plot(chiasm_DVH.histogram[0], chiasm_DVH.histogram[1], label=chiasm_DVH.name)
ax[1].plot(stem_DVH.histogram[0], stem_DVH.histogram[1], label=stem_DVH.name)
ax[1].set_xlabel("Dose (Gy)")
ax[1].set_ylabel("Volume (%)")
plt.grid(True)
plt.legend()

plt.show()
