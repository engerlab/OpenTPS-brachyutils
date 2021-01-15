
import os
import numpy as np
import scipy.sparse as sp
from matplotlib import pyplot as plt

from Process.PatientData import *
from Process.PlanOptimization import *
from Process.MCsquare import *
from Process.MCsquare_sparse_format import *
from Process.RTdose import *
from Process.DVH import *

# User config:
patient_data_path = "../python_interface/data/Prostate"
output_path = os.path.join(patient_data_path, "OpenTPS")

# Create output folder
if not os.path.isdir(output_path):
  os.mkdir(output_path)

# Load patient data
Patients = PatientList()
Patients.list_dicom_files(patient_data_path, 1)
Patients.print_patient_list()
Patients.list[0].import_patient_data() # import patient 0
Patients.list[0].RTstructs[0].print_ROINames()

# Configure MCsquare
mc2 = MCsquare()
mc2.BDL.selected_BDL = mc2.BDL.list[1] # UMCG_P1_v2_RangeShifter
mc2.Scanner.selected_Scanner = mc2.Scanner.list[0] # UCL_Toshiba
mc2.NumProtons = 5e4
mc2.dose2water = True
mc2.SetupSystematicError = [5.0, 5.0, 5.0] # mm
mc2.SetupRandomError = [0.0, 0.0, 0.0] # mm (sigma)
mc2.RangeSystematicError = 3.0 # %
mc2.Robustness_Strategy = "ErrorSpace_regular"

# Plan parameters:
ct = Patients.list[0].CTimages[0]
Target = Patients.list[0].RTstructs[0].Contours[10] # 7="PTV 74 gy", 10="MIROpt-structure"
OAR = Patients.list[0].RTstructs[0].Contours[6] # 4="Rectum", 6="Vessie"
BeamNames = ["Beam1", "Beam2"]
GantryAngles = [90., 270.]
CouchAngles = [0., 0.]
SpotSpacing = 7.0
LayerSpacing = 6.0
RTV_margin = max(SpotSpacing, LayerSpacing) + max(mc2.SetupSystematicError)
    
# Load / Generate new plan
plan_file = os.path.join(output_path, "RobustPlan.tps")
if os.path.isfile(plan_file):
  plan = RTplan()
  plan.load(plan_file)
else:
  plan = CreatePlanStructure(ct, Target, BeamNames, GantryAngles, CouchAngles, mc2.Scanner.selected_Scanner, RTV_margin=RTV_margin, SpotSpacing=SpotSpacing, LayerSpacing=LayerSpacing) # Spot placement
  plan.PlanName = "RobustPlan"
  mc2.MCsquare_beamlet_calculation(ct, plan, output_path)
  plan.save(plan_file)
Patients.list[0].Plans.append(plan)

# optimization objectives
plan.Objectives.setTarget(Target.ROIName, 60.0)
plan.Objectives.list = []
plan.Objectives.addObjective(Target.ROIName, "Dmax", "<", 60.0, 5.0, Robust=True)
plan.Objectives.addObjective(Target.ROIName, "Dmin", ">", 60.0, 5.0, Robust=True)
plan.Objectives.addObjective(OAR.ROIName, "Dmax", "<", 50.0, 1.0)
plan.Objectives.addObjective(OAR.ROIName, "Dmean", "<", 25.0, 1.0)

# Compute pre-optimization dose
dose_vector = plan.beamlets.Compute_dose_from_beamlets()
dose = RTdose().Initialize_from_beamlet_dose(plan.PlanName, plan.beamlets, dose_vector, ct)

# Compute DVH
Target_DVH = DVH(dose, Target)
OAR_DVH = DVH(dose, OAR)

# Find target center for display
maskY,maskX,maskZ = np.nonzero(Target.Mask)
target_center = [np.mean(maskX), np.mean(maskY), np.mean(maskZ)]
Z_coord = int(target_center[2])

# Display dose
plt.figure(figsize=(10,10))
plt.subplot(2,2,1)
plt.imshow(ct.Image[:,:,Z_coord], cmap='gray')
plt.imshow(Target.ContourMask[:,:,Z_coord], alpha=.2, cmap='binary') # PTV
plt.imshow(dose.Image[:,:,Z_coord], cmap='jet', alpha=.2)
plt.title("Pre-optimization dose")
plt.subplot(2,2,2)
plt.plot(Target_DVH.dose, Target_DVH.volume, label=Target_DVH.ROIName)
plt.plot(OAR_DVH.dose, OAR_DVH.volume, label=OAR_DVH.ROIName)
plt.title("Pre-optimization DVH")

# Optimize treatment plan
w, dose_vector, ps = OptimizeWeights(plan, Patients.list[0].RTstructs[0].Contours, method="Scipy-lBFGS")
dose = RTdose().Initialize_from_beamlet_dose(plan.PlanName, plan.beamlets, dose_vector, ct)
plan_file = os.path.join(output_path, "RobustPlan_optimized.tps")
plan.save(plan_file)

# Compute DVH
Target_DVH = DVH(dose, Target)
print('D95 = ' + str(Target_DVH.D95) + ' Gy')
OAR_DVH = DVH(dose, OAR)

# Display dose
plt.subplot(2,2,3)
plt.imshow(ct.Image[:,:,Z_coord], cmap='gray')
plt.imshow(Target.ContourMask[:,:,Z_coord], alpha=.2, cmap='binary') # PTV
plt.imshow(dose.Image[:,:,Z_coord], cmap='jet', alpha=.2)
plt.title("Optimized dose")
plt.subplot(2,2,4)
plt.plot(Target_DVH.dose, Target_DVH.volume, label=Target_DVH.ROIName)
plt.plot(OAR_DVH.dose, OAR_DVH.volume, label=OAR_DVH.ROIName)
plt.title("Optimized DVH")
plt.show()
