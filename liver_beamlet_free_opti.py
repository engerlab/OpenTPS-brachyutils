
import os
import numpy as np
import scipy.sparse as sp
from matplotlib import pyplot as plt
import pickle

from Process.PatientData import *
from Process.PlanOptimization import *
from Process.MCsquare import *
from Process.MCsquare_sparse_format import *
from Process.RTdose import *
from Process.DVH import *
from Process.MCsquare_plan import *

def get_standard_metrics(DHV):
    return {'Dmean':DHV.Dmean, 'Dmin':DHV.Dmin, 'Dmax':DHV.Dmax, 
    'D98':DHV.D98, 'D95':DHV.D95, 'D50':DHV.D50, 
    'D5':DHV.D5, 'D2':DHV.D2}

overwrite = True # overwrite plan

def optimize_liver_treatment_beamlet_free(patient_data_path, target_number=21, OAR_opti_number=[22,6], plot_results=False):
  # User config:
  # patient_data_path = "/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/4DCT/p0"
  output_path = os.path.join(patient_data_path, "OpenTPS")

  # Create output folder
  if not os.path.isdir(output_path):
    os.mkdir(output_path)

  # Load patient data
  Patients = PatientList()
  Patients.list_dicom_files(patient_data_path, 1)
  #Patients.print_patient_list()
  Patients.list[0].import_patient_data() # import patient 0
  #Patients.list[0].RTstructs[0].print_ROINames()

  # Configure MCsquare
  mc2 = MCsquare()
  mc2.BDL.selected_BDL = mc2.BDL.list[1] # UMCG_P1_v2_RangeShifter
  mc2.BDL.import_BDL()
  RS = mc2.BDL.RangeShifters[0]
  mc2.Scanner.selected_Scanner = mc2.Scanner.list[0] # UCL_Toshiba
  mc2.NumProtons = 1e7
  mc2.dose2water = True
  # new
  mc2.PlanOptimization = "beamlet-free"

  # Plan parameters:
  ct = Patients.list[0].CTimages[0]
  Target = Patients.list[0].RTstructs[0].Contours[target_number] # 21 = MidP CT PTV 5mm
  OAR = []
  OAR.append(Patients.list[0].RTstructs[0].Contours[OAR_opti_number[0]]) # 22 =p0 Liver PTV 5mm (for optimization), 
  OAR.append(Patients.list[0].RTstructs[0].Contours[OAR_opti_number[1]]) # 6 = "Kidney R"
  OAR.append(Patients.list[0].RTstructs[0].Contours[23]) # 23 = "Liver - GTV" (for evaluation)
  OAR.append(Patients.list[0].RTstructs[0].Contours[13]) # Spinal cord
  OAR.append(Patients.list[0].RTstructs[0].Contours[10]) # PRV Spinal cord
  OAR.append(Patients.list[0].RTstructs[0].Contours[5]) # Heart
  OAR.append(Patients.list[0].RTstructs[0].Contours[14]) # Stomach
  OAR.append(Patients.list[0].RTstructs[0].Contours[3]) # Duodenum
  OAR.append(Patients.list[0].RTstructs[0].Contours[12]) # SmallBowel
  OAR.append(Patients.list[0].RTstructs[0].Contours[1]) # Chestwall

  if 0 <= 24 < len(Patients.list[0].RTstructs[0].Contours):
    OAR.append(Patients.list[0].RTstructs[0].Contours[24]) # 24 = "Liver - GTV" (for evaluation) for ITV


  ROI = [Target] + OAR # concatenation of Target and OAR
  BeamNames = ["Beam1", "Beam2", "Beam3"]
  GantryAngles = [180., 210., 240.]
  CouchAngles = [0., 0., 0.]
  RangeShifters = [RS, RS, RS]
      
  # Load / Generate new plan
  plan_file = os.path.join(output_path, "treatment_plan.tps")
  if os.path.isfile(plan_file) and not overwrite:
    plan = RTplan()
    plan.load(plan_file)
  else:
      plan = CreatePlanStructure(ct, Target, BeamNames, GantryAngles, CouchAngles, mc2.Scanner.selected_Scanner, RangeShifters=RangeShifters) # Spot placement
      plan.PlanName = "treatment_plan"
      #mc2.MCsquare_beamlet_calculation(ct, plan, output_path)
      plan.save(plan_file)
      Patients.list[0].Plans.append(plan)

  mc2.DoseName = plan.PlanName

  # optimization objectives
  plan.Objectives.setTarget(Target.ROIName, 50.0)
  plan.Objectives.list = []
  plan.Objectives.addObjective(Target.ROIName, "Dmax", "<", 50.0, 10.0)
  plan.Objectives.addObjective(Target.ROIName, "Dmin", ">", 50.0, 10.0)
  plan.Objectives.addObjective(OAR[0].ROIName, "Dmax", "<", 40.0, 1.0)
  plan.Objectives.addObjective(OAR[1].ROIName, "Dmax", "<", 40.0, 1.0)
  #plan.Objectives.addObjective(OAR.ROIName, "Dmean", "<", 25.0, 1.0)

  # Find target center for display
  maskY,maskX,maskZ = np.nonzero(Target.Mask)
  target_center = [np.mean(maskX), np.mean(maskY), np.mean(maskZ)]
  Z_coord = int(target_center[2])

  # Optimize treatment plan
  # run MCsquare optimization
  mhd_dose = mc2.BeamletFree_optimization(ct, plan, ROI)
  dose = RTdose().Initialize_from_MHD(mc2.DoseName, mhd_dose, ct, plan)

  # Save dose
  dose.export_Dicom(os.path.join(output_path, "dose_static.dcm"))

  # Save OpenTPS plan
  plan_file = os.path.join(output_path, "treatment_plan_optimized.tps")
  plan.save(plan_file)

  # Save MCsquare plan
  export_plan_for_MCsquare(plan, os.path.join(output_path, "PlanPencil.txt"), ct, mc2.BDL)

  # Compute DVH
  results = {}
  Target_DVH = DVH(dose, Target)
  results[Target.ROIName] = get_standard_metrics(Target_DVH)
  print('D95 = ' + str(Target_DVH.D95) + ' Gy')
  OAR_DVH = []
  for _oar in OAR:
      _dvh = DVH(dose, _oar)
      OAR_DVH.append(_dvh)
      results[_oar.ROIName] = get_standard_metrics(_dvh)
      if _oar.ROIName == 'Liver GTV' or 'Liver PTV 5mm' in _oar.ROIName:
        results[_oar.ROIName]['D700cc'] = _dvh.compute_Dcc(700.)
      if _oar.ROIName == 'MidP CT Heart':
        results[_oar.ROIName]['D10cc'] = _dvh.compute_Dcc(10.)
        results[_oar.ROIName]['D1cc'] = _dvh.compute_Dcc(1.)
      if _oar.ROIName == 'MidP CT Stomach':
        results[_oar.ROIName]['D10cc'] = _dvh.compute_Dcc(10.)
        results[_oar.ROIName]['D1cc'] = _dvh.compute_Dcc(1.)
      if _oar.ROIName == 'MidP CT Duodenum':
        results[_oar.ROIName]['D10cc'] = _dvh.compute_Dcc(10.)
        results[_oar.ROIName]['D5cc'] = _dvh.compute_Dcc(5.)
        results[_oar.ROIName]['D1cc'] = _dvh.compute_Dcc(1.)
      if _oar.ROIName == 'MidP CT SmallBowel':
        results[_oar.ROIName]['D5cc'] = _dvh.compute_Dcc(5.)
        results[_oar.ROIName]['D1cc'] = _dvh.compute_Dcc(1.)
      if _oar.ROIName == 'MidP CT Kidney R':
        results[_oar.ROIName]['D35'] = _dvh.compute_Dx(35)
      if _oar.ROIName == 'MidP CT Chestwall':
        results[_oar.ROIName]['D1cc'] = _dvh.compute_Dcc(1.)
        results[_oar.ROIName]['D30cc'] = _dvh.compute_Dcc(30.)

  pickle.dump(results, open(os.path.join(output_path, "results_static.pkl"), "wb"))

  if plot_results:
    plt.subplot(2,2,3)
    plt.imshow(ct.Image[:,:,Z_coord], cmap='gray')
    plt.imshow(Target.ContourMask[:,:,Z_coord], alpha=.2, cmap='binary') # PTV
    plt.imshow(dose.Image[:,:,Z_coord], cmap='jet', alpha=.2)
    plt.title("Optimized dose")
    plt.subplot(2,2,4)
    plt.plot(Target_DVH.dose, Target_DVH.volume, label=Target_DVH.ROIName)
    for _oar in OAR_DVH:
        plt.plot(_oar.dose, _oar.volume, label=_oar.ROIName)
    plt.title("Optimized DVH")
    plt.legend()
    plt.show()

def optimize_phases():
  patient_data_path = "/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/patient_0/4DCT/"
  phases = ['p40','p50','p60','p70','p80','p90']

  for p in phases:
    optimize_liver_treatment_beamlet_free(patient_data_path+p)

def optimize_MidP(ITV_based=True):
  patient_data_path = "/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/patient_0/MidP_CT/"
  # ITV based
  if ITV_based:
    optimize_liver_treatment_beamlet_free(patient_data_path, target_number=22, OAR_opti_number=[23,6])
  else: # Saint-Luc MidP based
    optimize_liver_treatment_beamlet_free(patient_data_path, target_number=11, OAR_opti_number=[16,6])

def save_MCsquare_treatment_plan(CT_path, tps_plan_path, output_path):
  # Load patient data
  Patients = PatientList()
  Patients.list_dicom_files(CT_path, 1)
  Patients.list[0].import_patient_data()
  ct = Patients.list[0].CTimages[0]

  # Configure MCsquare
  mc2 = MCsquare()
  mc2.BDL.selected_BDL = mc2.BDL.list[1] # UMCG_P1_v2_RangeShifter
  mc2.Scanner.selected_Scanner = mc2.Scanner.list[0] # UCL_Toshiba
  mc2.NumProtons = 1e4 # no need for much protons since we don't save a dose but plan parameters
  mc2.dose2water = True

  plan = RTplan()
  plan.load(tps_plan_path)

  mc2.init_simulation_directory()
    
  # Export CT image
  mc2.export_CT_for_MCsquare(ct, os.path.join(mc2.WorkDir, "CT.mhd"), mc2.Crop_CT_contour)

  # Export treatment plan
  mc2.BDL.import_BDL()
  export_plan_for_MCsquare(plan, os.path.join(output_path, "PlanPencil.txt"), ct, mc2.BDL)

  # mc2.MCsquare_simulation(ct, plan)


if __name__ == '__main__':
  # optimize_phases()
  optimize_MidP()

  # phases = ['p10','p20','p30','p40','p50','p60','p70','p80','p90']
  # for p in phases:
  #   CT_path = f"/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/4DCT/{p}"
  #   tps_plan_path =  f"/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/4DCT/{p}/OpenTPS/treatment_plan_optimized.tps"
  #   output_path = f"/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/4DCT/{p}/OpenTPS/"
  #   save_MCsquare_treatment_plan(CT_path, tps_plan_path, output_path)

  # CT_path = f"/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/MidP_CT"
  # tps_plan_path =  f"/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/MidP_CT/OpenTPS/treatment_plan_optimized.tps"
  # output_path = f"/mnt/c/Users/vhamaide/Desktop/UCL/ARIES/data/liver/MidP_CT/OpenTPS/"
  # save_MCsquare_treatment_plan(CT_path, tps_plan_path, output_path)