import json
import logging.config
import os
import sys

sys.path.append('..')
import numpy as np
from matplotlib import pyplot as plt
from Core.Data.Images import CTImage
from Core.Data.Images import ROIMask
from Core.Data.Plan import ObjectivesList
from Core.Data.Plan import PlanDesign
from Core.Data import DVH
from Core.Data import Patient
from Core.Data import PatientList
from Core.Data.Plan._objectivesList import FidObjective
from Core.IO import mcsquareIO
from Core.IO.scannerReader import readScanner
from Core.IO.serializedObjectIO import loadDataStructure, loadRTPlan, saveRTPlan
from Core.Processing.DoseCalculation.doseCalculationConfig import DoseCalculationConfig
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing.resampler3D import resampleImage3DOnImage3D
from Core.Processing.PlanOptimization.Objectives.doseFidelity import DoseFidelity
from Core.Processing.PlanOptimization.planOptimization import IMPTPlanOptimizer

with open('../config/logger/logging_config.json', 'r') as log_fid:
    config_dict = json.load(log_fid)
logging.config.dictConfig(config_dict)

# Generic example: box of water with squared target
patientList = PatientList()

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
roi.color = (255, 0, 0)  # red
data = np.zeros((ctSize, ctSize, ctSize)).astype(bool)
data[100:120, 100:120, 100:120] = True
roi.imageArray = data

examplePath = "../testData"
patient_data_path = os.path.join(examplePath, "fakeCT")
output_path = os.path.join(patient_data_path, "OpenTPS")

# Design plan
beamNames = ["Beam1"]
gantryAngles = [0.]
couchAngles = [0.]

# Create output folder
if not os.path.isdir(output_path):
    os.mkdir(output_path)

# Configure MCsquare
mc2 = MCsquareDoseCalculator()
mc2.beamModel = bdl
mc2.nbPrimaries = 5e4
mc2.ctCalibration = ctCalibration
mc2._setupSystematicError = [5.0, 5.0, 5.0]  # mm
mc2._setupRandomError = [0.0, 0.0, 0.0]  # mm (sigma)
mc2._rangeSystematicError = 3.0  # %
mc2._robustnessStrategy = "ErrorSpace_regular"

# Load / Generate new plan
plan_file = os.path.join(output_path, "RobustPlan_notCropped.tps")

if os.path.isfile(plan_file):
    plan = loadRTPlan(plan_file)
else:
    planInit = PlanDesign()
    planInit.ct = ct
    planInit.targetMask = roi
    planInit.gantryAngles = gantryAngles
    planInit.beamNames = beamNames
    planInit.couchAngles = couchAngles
    planInit.calibration = ctCalibration
    planInit.spotSpacing = 7.0
    planInit.layerSpacing = 6.0
    planInit.targetMargin = max(planInit.spotSpacing, planInit.layerSpacing) + max(mc2._setupSystematicError)

    plan = planInit.buildPlan()  # Spot placement
    plan.PlanName = "RobustPlan"

    #mc2.computeBeamlets(ct, plan, output_path, roi=[roi])
    mc2.computeBeamlets(ct, plan, output_path)
    #saveRTPlan(plan, plan_file)



beamletMatrix = plan.planDesign.beamlets.toSparseMatrix()
plan.planDesign.beamlets.load()
saveRTPlan(plan, plan_file)
plan.planDesign.objectives = ObjectivesList()
plan.planDesign.objectives.setTarget(roi.name, 20.0)
plan.planDesign.objectives.setScoringParameters(ct)
# scoringGridSize = [int(math.floor(i / j * k)) for i, j, k in zip(ct.gridSize, scoringSpacing, ct.spacing)]
# plan.planDesign.objectives.setScoringParameters(ct, scoringGridSize, scoringSpacing)
plan.planDesign.objectives.fidObjList = []
plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMAX, 20.0, 1.0, robust=True)
plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMIN, 20.5, 1.0, robust=True)

solver = IMPTPlanOptimizer(method='Scipy-LBFGS', plan=plan, maxit=50)
# Optimize treatment plan
w, doseImage, ps = solver.optimize()

# MCsquare simulation
# mc2.nbPrimaries = 1e6
# doseImage = mc2.computeDose(ct, plan)

# Compute DVH
target_DVH = DVH(roi, doseImage)
print('D95 = ' + str(target_DVH.D95) + ' Gy')
print('D5 = ' + str(target_DVH.D5) + ' Gy')
print('D5 - D95 =  {} Gy'.format(target_DVH.D5 - target_DVH.D95))

# center of mass
roi = resampleImage3DOnImage3D(roi, ct)
COM_coord = roi.centerOfMass
COM_index = roi.getVoxelIndexFromPosition(COM_coord)
Z_coord = COM_index[2]

img_ct = ct.imageArray[:, :, Z_coord].transpose(1, 0)
contourTargetMask = roi.getBinaryContourMask()
img_mask = contourTargetMask.imageArray[:, :, Z_coord].transpose(1, 0)
img_dose = resampleImage3DOnImage3D(doseImage, ct)
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
ax[1].set_xlabel("Dose (Gy)")
ax[1].set_ylabel("Volume (%)")
plt.grid(True)
plt.legend()

plt.show()
