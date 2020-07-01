
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

# user config:
patient_data_path = "../python_interface/data/Prostate"

# Load patient data
Patients = PatientList()
Patients.list_dicom_files(patient_data_path, 1)
Patients.print_patient_list()
Patients.list[0].import_patient_data() # import patient 0

# Configure MCsquare
mc2 = MCsquare()
mc2.BDL.selected_BDL = mc2.BDL.list[1] # UMCG_P1_v2_RangeShifter
mc2.Scanner.selected_Scanner = mc2.Scanner.list[0] # UCL_Toshiba
mc2.NumProtons = 5e4
mc2.dose2water = True

# Plan parameters:
ct = Patients.list[0].CTimages[0]
Target = Patients.list[0].RTstructs[0].Contours[7] # PTV
OAR = Patients.list[0].RTstructs[0].Contours[4] # Rectum
BeamNames = ["Beam1", "Beam2"]
GantryAngles = [90., 270.]
CouchAngles = [0., 0.]
    
# Generate new plan
plan = CreatePlanStructure(ct, Target, BeamNames, GantryAngles, CouchAngles, mc2.Scanner.selected_Scanner) # Spot placement
plan.PlanName = "NewPlan"
Patients.list[0].Plans.append(plan)

# optimization objectives
plan.Objectives.setTarget("PTV 74 gy", 60.0)
plan.Objectives.list = []
plan.Objectives.addObjective("PTV 74 gy", "Dmax", "<", 60.0, 5.0)
plan.Objectives.addObjective("PTV 74 gy", "Dmin", ">", 60.0, 5.0)
plan.Objectives.addObjective("Rectum", "Dmax", "<", 50.0, 1.0)
plan.Objectives.addObjective("Rectum", "Dmean", "<", 25.0, 1.0)

# Compute beamlets
beamlet_file = os.path.join(patient_data_path, "BeamletMatrix")
if os.path.isfile(beamlet_file):
  beamlets = MCsquare_sparse_format()
  beamlets.load(beamlet_file)
  beamlets.print_memory_usage()
else:
  beamlets = mc2.MCsquare_beamlet_calculation(ct, plan) # already scaled to Gray units
  beamlets.save(beamlet_file)
plan.beamlets = beamlets

# Compute pre-optimization dose
dose_vector = sp.csc_matrix.dot(beamlets.BeamletMatrix, beamlets.Weights)
dose = RTdose()
dose.Image = np.reshape(dose_vector, ct.GridSize, order='F')
dose.Image = np.flip(dose.Image, (0,1)).transpose(1,0,2)

# Compute DVH
Target_DVH = DVH(dose, Target)
OAR_DVH = DVH(dose, OAR)

# Display dose
plt.figure(figsize=(10,10))
plt.subplot(2,2,1)
plt.imshow(ct.Image[:,:,43], cmap='gray')
plt.imshow(Target.ContourMask[:,:,43], alpha=.2, cmap='binary') # PTV
plt.imshow(dose.Image[:,:,43], cmap='jet', alpha=.2)
plt.title("Pre-optimization dose")
plt.subplot(2,2,2)
plt.plot(Target_DVH.dose, Target_DVH.volume, label=Target_DVH.ROIName)
plt.plot(OAR_DVH.dose, OAR_DVH.volume, label=OAR_DVH.ROIName)
plt.title("Pre-optimization DVH")

# Optimize treatment plan
#w, dose_vector, ps = OptimizeWeights(plan, Patients.list[0].RTstructs[0].Contours, method="Scipy-lBFGS")
#w, dose_vector, ps = OptimizeWeights(plan, Patients.list[0].RTstructs[0].Contours, method="Gradient")
w, dose_vector, ps = OptimizeWeights(plan, Patients.list[0].RTstructs[0].Contours, method="FISTA")
beamlets.Weights = np.array(w, dtype=np.float32)
dose.Image = np.reshape(dose_vector, ct.GridSize, order='F')
dose.Image = np.flip(dose.Image, (0,1)).transpose(1,0,2)

# Compute DVH
Target_DVH = DVH(dose, Target)
print('D95 = ' + str(Target_DVH.D95) + ' Gy')
OAR_DVH = DVH(dose, OAR)

# Display dose
plt.subplot(2,2,3)
plt.imshow(ct.Image[:,:,43], cmap='gray')
plt.imshow(Target.ContourMask[:,:,43], alpha=.2, cmap='binary') # PTV
plt.imshow(dose.Image[:,:,43], cmap='jet', alpha=.2)
plt.title("Optimized dose")
plt.subplot(2,2,4)
plt.plot(Target_DVH.dose, Target_DVH.volume, label=Target_DVH.ROIName)
plt.plot(OAR_DVH.dose, OAR_DVH.volume, label=OAR_DVH.ROIName)
plt.title("Optimized DVH")
plt.show()
