import numpy as np
from matplotlib import pyplot as plt
from opentps.core.data import Patient, DVH
from opentps.core.data.images import CTImage, ROIMask
from opentps.core.data.plan import PlanDesign, ObjectivesList, FidObjective

from opentps.core.io import mcsquareIO
from opentps.core.io.scannerReader import readScanner
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.processing.imageProcessing.resampler3D import resampleImage3DOnImage3D
from opentps.core.processing.planOptimization.objectives.doseFidelity import DoseFidelity
from opentps.core.processing.planOptimization.planOptimization import IMPTPlanOptimizer

ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)
bdl = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)

patient = Patient()
patient.name = 'Patient'

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

beamNames = ["Beam1"]
gantryAngles = [0.]
couchAngles = [0.]

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

mc2 = MCsquareDoseCalculator()
mc2.beamModel = bdl
mc2.nbPrimaries = 5e3
mc2.ctCalibration = ctCalibration
mc2.independentScoringGrid = True
mc2.scoringVoxelSpacing = 2.


beamlets = mc2.computeBeamlets(ct, plan, roi=[roi])

plan.planDesign.beamlets = beamlets
beamletMatrix = plan.planDesign.beamlets.toSparseMatrix()

doseImage = plan.planDesign.beamlets.toDoseImage()
doseImage.patient = patient

plan.planDesign.objectives = ObjectivesList()
plan.planDesign.objectives.setTarget(roi.name, 20.0)
plan.planDesign.objectives.setScoringParameters(ct, mc2.scoringGridSize, mc2.scoringVoxelSpacing)
plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMAX, 20.0, 1.0)
plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMIN, 20.0, 1.0)
objectiveFunction = DoseFidelity(plan, beamletMatrix)

solver = IMPTPlanOptimizer(method='Scipy-LBFGS', plan=plan, functions=[objectiveFunction], maxit=50)

w, doseImage, ps = solver.optimize()

doseImage.patient = patient

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
