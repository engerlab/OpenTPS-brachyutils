import copy
import json
import logging.config
import os

import numpy as np
from matplotlib import pyplot as plt

import opentps
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
from Core.IO.serializedObjectIO import loadDataStructure, saveRTPlan, loadRTPlan, loadBeamlets, saveBeamlets
from Core.Processing.DoseCalculation.doseCalculationConfig import DoseCalculationConfig
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing.resampler3D import resampleImage3DOnImage3D
from Core.Processing.PlanOptimization.Objectives.doseFidelity import DoseFidelity
from Core.Processing.PlanOptimization.planOptimization import IMPTPlanOptimizer


# Generic example: box of water with squared target
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
data[80:100, 100:120, 120:140] = True
roi.imageArray = data

examplePath = "/home/sophie/Documents/Protontherapy/OpenTPS/refactor/opentps/testData"

output_path = os.path.join(examplePath, "fakeCT")


# Design plan
beamNames = ["Beam1"]
gantryAngles = [0.]
couchAngles = [0.]

# method 1 : create or load existing plan (no workflow)

# Configure MCsquare
mc2 = MCsquareDoseCalculator()
mc2.beamModel = bdl
mc2.nbPrimaries = 5e4
mc2.ctCalibration = ctCalibration

#mc2.independentScoringGrid = True
#scoringSpacing = [2, 2, 2]
#mc2.scoringVoxelSpacing = scoringSpacing

# Load / Generate new plan
plan_file = os.path.join(output_path, "Plan_WaterPhantom_.tps")

if os.path.isfile(plan_file):
    plan = loadRTPlan(plan_file)
    print('Plan loaded')
    # not cropped
    beamletPath = os.path.join(output_path,
                               "BeamletMatrix_1.2.826.0.1.3680043.8.498.11493239558261298828819948370674664388.1.blm")
    plan.planDesign.beamlets = loadBeamlets(beamletPath)
    beamletMatrix = plan.planDesign.beamlets.toSparseMatrix()
9
else:
    planInit = PlanDesign()
    planInit.ct = ct
    planInit.targetMask = roi
    planInit.gantryAngles = gantryAngles
    planInit.beamNames = beamNames
    planInit.couchAngles = couchAngles
    planInit.calibration = ctCalibration
    planInit.spotSpacing = 5.0
    planInit.layerSpacing = 5.0
    planInit.targetMargin = 5.0

    plan = planInit.buildPlan()  # Spot placement
    plan.PlanName = "NewPlan"
    #saveRTPlan(plan, plan_file)

    roiDilated = ROIMask.fromImage3D(roi)
    roiDilated.dilate(planInit.targetMargin*3)
    beamlets = mc2.computeBeamlets(ct, plan, roi=[roiDilated])
    #beamlets = mc2.computeBeamlets(ct, plan)
    plan.planDesign.beamlets = beamlets
    outputBeamletFile = os.path.join(output_path, "BeamletMatrix_Cropped" + plan.seriesInstanceUID + ".blm")
    #saveBeamlets(beamlets, outputBeamletFile)
    beamletMatrix = plan.planDesign.beamlets.toSparseMatrix()

plan.planDesign.objectives = ObjectivesList()
plan.planDesign.objectives.setTarget(roi.name, 20.0)
plan.planDesign.objectives.setScoringParameters(ct)
#scoringGridSize = [int(math.floor(i / j * k)) for i, j, k in zip(ct.gridSize, scoringSpacing, ct.spacing)]
#plan.planDesign.objectives.setScoringParameters(ct, scoringGridSize, scoringSpacing)
plan.planDesign.objectives.fidObjList = []
plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMAX, 20.0, 1.0)
plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMIN, 20.0, 1.0)
#plan.planDesign.defineTargetMaskAndPrescription()
objectiveFunction = DoseFidelity(plan.planDesign.objectives.fidObjList, beamletMatrix)
print('fidelity init done')

solver = IMPTPlanOptimizer(method='Scipy-LBFGS', plan=plan, functions=[objectiveFunction], maxit=50)
# Optimize treatment plan
w, doseImage, ps = solver.optimize()

# MCsquare simulation
#mc2.nbPrimaries = 1e6
#doseImage = mc2.computeDose(ct, plan)

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
