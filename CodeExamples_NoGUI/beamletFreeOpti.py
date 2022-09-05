import os
from matplotlib import pyplot as plt


from Core.IO import mcsquareIO
from Core.IO.dataLoader import loadAllData
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Data.CTCalibrations.MCsquareCalibration.mcsquareCTCalibration import MCsquareCTCalibration
from Core.IO.serializedObjectIO import loadRTPlan, saveRTPlan, loadBeamlets
from Core.Data.Plan.objectivesList import ObjectivesList
from Core.Data.dvh import DVH
# CT path
from Core.Processing.ImageProcessing.resampler3D import resampleImage3DOnImage3D

ctImagePath = "/home/sophie/Documents/Protontherapy/OpenTPS/arc_dev/opentps/data/Plan_IMPT_patient1"
# Output path
output_path = os.path.join(ctImagePath, "OpenTPS")

# Load patient data
dataList = loadAllData(ctImagePath, maxDepth=0)
ct = dataList[7]
contours = dataList[6]
print('Available ROIs')
contours.print_ROINames()

# Configure MCsquare
MCSquarePath = '../Core/Processing/DoseCalculation/MCsquare/'
mc2 = MCsquareDoseCalculator()
beamModel = mcsquareIO.readBDL(os.path.join(MCSquarePath, 'BDL', 'UMCG_P1_v2_RangeShifter.txt'))
mc2.beamModel = beamModel
# small number of primaries for beamlet calculation
mc2.nbPrimaries = 1e7

scannerPath = os.path.join(MCSquarePath, 'Scanners', 'UCL_Toshiba')
calibration = MCsquareCTCalibration(fromFiles=(os.path.join(scannerPath, 'HU_Density_Conversion.txt'),
                                               os.path.join(scannerPath, 'HU_Material_Conversion.txt'),
                                               os.path.join(MCSquarePath, 'Materials')))
mc2.ctCalibration = calibration

# ROIs
target = contours.getContourByName('CTV')
targetMask = target.getBinaryMask(origin=ct.origin, gridSize=ct.gridSize, spacing=ct.spacing)
opticChiasm = contours.getContourByName('Optic Chiasm')
brainStem = contours.getContourByName('Brain Stem')

L = []
for i in range(len(contours)):
    L.append(contours[i].name)

#ROI = [body.name]
ROI = [target.name, opticChiasm.name, brainStem.name, body.name]

# Crop Beamlets on ROI to save computation time ! not mandatory
ROIforBL = []
for i in range(len(ROI)):
    index_value = L.index(ROI[i])
    # add contour
    ROIforBL.append(contours[index_value])

# Load plan
#plan_file = os.path.join(output_path, "test2RefactorPlan.tps")
plan_file = os.path.join(output_path, "plan_brain_0_45.tps")
if os.path.isfile(plan_file):
    plan = loadRTPlan(plan_file)
    print('Plan loaded')
else:
    print('Path is wrong or plan does not exist')

# optimization objectives
plan.objectives = ObjectivesList()
plan.objectives.setTarget(target.name, 65.0)
plan.objectives.fidObjList = []
plan.objectives.addFidObjective(target.name, "Dmax", "<", 65.0, 1.)
plan.objectives.addFidObjective(target.name, "Dmin", ">", 65.0, 1.0)

plan_filepath = os.path.join(output_path, "NewPlan_optimized.tps")
# saveRTPlan(plan, plan_filepath)

# MCsquare beamlet free optimization
#doseImage = mc2.optimizeBeamletFree(ct, plan, [target])
doseImage = mc2.optimizeBeamletFree(ct, plan, ROIforBL)

# Compute DVH
target_DVH = DVH(target, doseImage)
chiasm_DVH = DVH(opticChiasm, doseImage)
stem_DVH = DVH(brainStem, doseImage)

print('D95 = ' + str(target_DVH.D95) + ' Gy')
print('D5 = ' + str(target_DVH.D5) + ' Gy')
print('D5 - D95 =  {} Gy'.format(target_DVH.D5 - target_DVH.D95))
print("Dmax",target_DVH._Dmax)
print("Dmin",target_DVH._Dmin)

# center of mass
COM_coord = targetMask.centerOfMass
COM_index = targetMask.getVoxelIndexFromPosition(COM_coord)
Z_coord = COM_index[2]

img_ct = ct.imageArray[:, :, Z_coord].transpose(1, 0)
contourTargetMask = target.getBinaryContourMask(origin=ct.origin, gridSize=ct.gridSize, spacing=ct.spacing)
img_mask = contourTargetMask.imageArray[:, :, Z_coord].transpose(1, 0)
#img_dose = resampleImage3DOnImage3D(doseImage, ct)
img_dose = doseImage.imageArray[:, :, Z_coord].transpose(1, 0)

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