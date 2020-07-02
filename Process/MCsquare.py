import os
import numpy as np
import scipy.sparse as sp
import subprocess

from Process.MHD_image import *
from Process.MCsquare_BDL import *
from Process.MCsquare_CT_calibration import *
from Process.MCsquare_plan import *
from Process.MCsquare_config import *
from Process.MCsquare_sparse_format import *
from Process.RTdose import *
from Process.RobustnessTest import *

class MCsquare:

  def __init__(self):
    self.Path_MCsquareLib = os.path.abspath("./MCsquare")
    self.WorkDir = os.path.join(os.path.expanduser('~'), "Work");
    self.DoseName = "MCsquare_dose"
    self.BDL = MCsquare_BDL()
    self.Scanner = MCsquare_CT_calibration()
    self.NumProtons = 1e7
    self.MaxUncertainty = 2.0
    self.dose2water = 1
    self.PlanOptimization = "none" # possible options: none, beamlet-free
    self.config = {}
    self.SetupSystematicError = [2.5, 2.5, 2.5] # mm
    self.SetupRandomError = [1.0, 1.0, 1.0] # mm
    self.RangeSystematicError = 3.0 # %
    
  
  
  def MCsquare_simulation(self, CT, Plan):
    print("Prepare MCsquare simulation")
  
    self.init_simulation_directory()
      
    # Export CT image
    self.export_CT_for_MCsquare(CT, os.path.join(self.WorkDir, "CT.mhd"))
    
    # Export treatment plan
    self.BDL.import_BDL()
    export_plan_for_MCsquare(Plan, os.path.join(self.WorkDir, "PlanPencil.txt"), CT, self.BDL)
    
    # Generate MCsquare configuration file
    self.config = generate_MCsquare_config(self.WorkDir, self.NumProtons, self.Scanner.get_path(), self.BDL.get_path(), 'CT.mhd', 'PlanPencil.txt')
    if(self.dose2water > 0): self.config["Dose_to_Water_conversion"] = "OnlineSPR"
    else: self.config["Dose_to_Water_conversion"] = "Disabled"
    self.config["Stat_uncertainty"] = self.MaxUncertainty
    export_MCsquare_config(self.config)
    
    # Start simulation
    print("\nStart MCsquare simulation")
    os.system("cd " + self.WorkDir + " && " + os.path.join(self.Path_MCsquareLib, "MCsquare"))
    
    # Import dose result
    mhd_dose = self.import_MCsquare_dose(Plan)
    
    return mhd_dose



  def MCsquare_RobustScenario_calculation(self, CT, Plan, Target, TargetPrescription):
    # Initialize robustness test object
    scenarios = RobustnessTest()
    scenarios.SelectionStrategy = "Dosimetric"
    scenarios.SetupSystematicError = self.SetupSystematicError
    scenarios.SetupRandomError = self.SetupRandomError
    scenarios.RangeSystematicError = self.RangeSystematicError
    scenarios.Target = Target
    scenarios.TargetPrescription = TargetPrescription
  
    self.init_simulation_directory()
      
    # Export CT image
    self.export_CT_for_MCsquare(CT, os.path.join(self.WorkDir, "CT.mhd"))
    
    # Export treatment plan
    self.BDL.import_BDL()
    export_plan_for_MCsquare(Plan, os.path.join(self.WorkDir, "PlanPencil.txt"), CT, self.BDL)
    
    # Generate MCsquare configuration file
    self.config = generate_MCsquare_config(self.WorkDir, self.NumProtons, self.Scanner.get_path(), self.BDL.get_path(), 'CT.mhd', 'PlanPencil.txt')
    if(self.dose2water > 0): self.config["Dose_to_Water_conversion"] = "OnlineSPR"
    else: self.config["Dose_to_Water_conversion"] = "Disabled"
    self.config["Stat_uncertainty"] = self.MaxUncertainty
    export_MCsquare_config(self.config)
    
    # Start nominal simulation
    print("\nSimulation of nominal scenario")
    os.system("cd " + self.WorkDir + " && " + os.path.join(self.Path_MCsquareLib, "MCsquare"))  
    
    # Import dose result
    mhd_dose = self.import_MCsquare_dose(Plan)
    dose = RTdose().Initialize_from_MHD(self.DoseName+"_Nominal", mhd_dose, CT)
    scenarios.setNominal(dose)

    # Import number of particles from previous simulation
    NumParticles, StatUncertainty = self.get_simulation_progress()

    # Configure simulation of error scenarios
    self.config["Num_Primaries"] = NumParticles
    self.config["Compute_stat_uncertainty"] = False
    self.config["Robustness_Mode"] = True
    self.config["Scenario_selection"] = "Random"
    self.config["Simulate_nominal_plan"] = False
    self.config["Num_Random_Scenarios"] = 100
    self.config["Systematic_Setup_Error"] = [self.SetupSystematicError[0]/10, self.SetupSystematicError[1]/10, self.SetupSystematicError[2]/10] # cm
    self.config["Random_Setup_Error"] = [self.SetupRandomError[0]/10, self.SetupRandomError[1]/10, self.SetupRandomError[2]/10] # cm
    self.config["Systematic_Range_Error"] = self.RangeSystematicError # %
    export_MCsquare_config(self.config)

    # Start simulation of error scenarios
    print("\nSimulation of error scenarios")
    os.system("cd " + self.WorkDir + " && " + os.path.join(self.Path_MCsquareLib, "MCsquare")) 

    # command = os.path.join(self.Path_MCsquareLib, "MCsquare") 
    # process = subprocess.Popen([command], cwd=self.WorkDir, stdout=subprocess.PIPE, shell=True)
    # while True:
    #   output = process.stdout.readline()
    #   if output: print(output.strip())
    #   elif process.poll() is not None: break
    # rc = process.poll()
    # print(rc)

    # Import dose results
    for s in range(self.config["Num_Random_Scenarios"]):
      FileName = 'Dose_Scenario_' + str(s+1) + '-' + str(self.config["Num_Random_Scenarios"]) + '.mhd'
      FilePath = os.path.join(self.WorkDir, "Outputs", FileName)
      if os.path.isfile(FilePath):
        mhd_dose = self.import_MCsquare_dose(Plan, FileName=FileName)
        dose = RTdose().Initialize_from_MHD(self.DoseName+"_Nominal", mhd_dose, CT)
        scenarios.addScnenario(dose)

    return scenarios
  
  
  def MCsquare_beamlet_calculation(self, CT, Plan):
    print("Prepare MCsquare beamlet calculation")
  
    self.init_simulation_directory()
      
    # Export CT image
    self.export_CT_for_MCsquare(CT, os.path.join(self.WorkDir, "CT.mhd"))
    
    # Export treatment plan
    self.BDL.import_BDL()
    export_plan_for_MCsquare(Plan, os.path.join(self.WorkDir, "PlanPencil.txt"), CT, self.BDL)
    
    # Generate MCsquare configuration file
    self.config = generate_MCsquare_config(self.WorkDir, self.NumProtons, self.Scanner.get_path(), self.BDL.get_path(), 'CT.mhd', 'PlanPencil.txt')
    if(self.dose2water > 0): self.config["Dose_to_Water_conversion"] = "OnlineSPR"
    else: self.config["Dose_to_Water_conversion"] = "Disabled"
    self.config["Compute_stat_uncertainty"] = False
    self.config["Beamlet_Mode"] = True
    self.config["Beamlet_Parallelization"] = True
    self.config["Dose_MHD_Output"] = False
    self.config["Dose_Sparse_Output"] = True
    export_MCsquare_config(self.config)
    
    # Start simulation
    print("\nStart MCsquare simulation")
    os.system("cd " + self.WorkDir + " && " + os.path.join(self.Path_MCsquareLib, "MCsquare"))   
    
    # Import sparse beamlets
    Beamlets = MCsquare_sparse_format()
    beamlet_file = os.path.join(self.WorkDir, "Outputs", "Sparse_Dose.txt")
    Beamlets.import_Sparse_Beamlets(beamlet_file, Plan.BeamletRescaling)

    return Beamlets
    
  
  
  def BeamletFree_optimization(self, CT, Plan, Contours):
    print("Prepare MCsquare optimization")
  
    self.init_simulation_directory()
      
    # Export CT image
    self.export_CT_for_MCsquare(CT, os.path.join(self.WorkDir, "CT.mhd"))
    
    # Export treatment plan
    self.BDL.import_BDL()
    export_plan_for_MCsquare(Plan, os.path.join(self.WorkDir, "PlanPencil.txt"), CT, self.BDL)
    
    # Export optimization objectives
    self.export_objectives_for_MCsquare(Plan.Objectives, os.path.join(self.WorkDir, "PlanObjectives.txt"))    
    
    # Export contours
    for contour in Contours:
      self.export_contour_for_MCsquare(contour, os.path.join(self.WorkDir, "structs"))
    
    # Generate MCsquare configuration file
    self.config = generate_MCsquare_config(self.WorkDir, self.NumProtons, self.Scanner.get_path(), self.BDL.get_path(), 'CT.mhd', 'PlanPencil.txt')
    if(self.dose2water > 0): self.config["Dose_to_Water_conversion"] = "OnlineSPR"
    else: self.config["Dose_to_Water_conversion"] = "Disabled"
    self.config["Compute_stat_uncertainty"] = False
    self.config["Optimization_Mode"] = True
    export_MCsquare_config(self.config)
    
    # Start simulation
    print("\nStart MCsquare simulation")
    os.system("cd " + self.WorkDir + " && " + os.path.join(self.Path_MCsquareLib, "MCsquare_opti"))
    
    # Import optimized plan
    file_path = os.path.join(self.config["WorkDir"], "Outputs", "Optimized_Plan.txt")
    update_weights_from_PlanPencil(file_path, CT, Plan, self.BDL)
    
    # Import dose result
    mhd_dose = self.import_MCsquare_dose(Plan)
    
    return mhd_dose
    
    
    
  def import_MCsquare_dose(self, plan, FileName="Dose.mhd", DoseScaling=1.0):
  
    dose_file = os.path.join(self.WorkDir, "Outputs", FileName)
  
    if not os.path.isfile(dose_file):
      print("ERROR: file " + dose_file + " not found!")
      return None
    else: print("Read dose file: " + dose_file)
  
    mhd_image = MHD_image()
    mhd_image.import_MHD_header(dose_file)
    mhd_image.import_MHD_data()
  
    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    mhd_image.Image = np.flip(mhd_image.Image, 0)
    mhd_image.Image = np.flip(mhd_image.Image, 1)
  
    # Convert in Gray units
    mhd_image.Image = mhd_image.Image * 1.602176e-19 * 1000 * plan.DeliveredProtons * plan.NumberOfFractionsPlanned * DoseScaling;
  
    return mhd_image
    
    
    
  def export_CT_for_MCsquare(self, CT, file_path):
  
    if CT.GridSize[0] != CT.GridSize[1]:
      print("WARNING: different number of voxels in X and Y directions may not be fully supported")  

    mhd_image = CT.convert_to_MHD()
  
    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    mhd_image.Image = np.flip(mhd_image.Image, 0)
    mhd_image.Image = np.flip(mhd_image.Image, 1)

    # export image
    mhd_image.export_MHD_header(file_path)
    mhd_image.export_MHD_data()
  
  
  
  def export_contour_for_MCsquare(self, Contour, folder_path):

    if not os.path.isdir(folder_path):
      os.mkdir(folder_path)
    
    mhd_image = Contour.convert_to_MHD()
  
    # Convert data for compatibility with MCsquare
    # These transformations may be modified in a future version
    mhd_image.Image = np.flip(mhd_image.Image, 0)
    mhd_image.Image = np.flip(mhd_image.Image, 1)
    
    # generate output path
    ContourName = Contour.ROIName.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')
    file_path = os.path.join(folder_path, ContourName + ".mhd")
  
    # export image
    mhd_image.export_MHD_header(file_path)
    mhd_image.export_MHD_data()
    
    
  
  def export_objectives_for_MCsquare(self, objectives, file_path):
    DestFolder, DestFile = os.path.split(file_path)
    
    TargetName = objectives.TargetName.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')
    
    print("Write plan objectives: " + file_path)
    fid = open(file_path,'w');
    fid.write("# List of objectives for treatment plan optimization\n\n") 
    fid.write("Target_ROIName:\n" + TargetName + "\n\n") 
    fid.write("Dose_prescription:\n" + str(objectives.TargetPrescription) + "\n\n") 
    fid.write("Number_of_objectives:\n" + str(len(objectives.list)) + "\n\n")
    
    for objective in objectives.list:
      ContourName = objective.ROIName.replace(' ', '_').replace('-', '_').replace('.', '_').replace('/', '_')
    
      fid.write("Objective_parameters:\n")
      fid.write("ROIName = " + ContourName + "\n")
      fid.write("Weight = " + str(objective.Weight) + "\n")
      fid.write(objective.Metric + " " + objective.Condition + " " + str(objective.LimitValue) + "\n")
      fid.write("\n")
      
    fid.close()
    


  def get_simulation_progress(self):
    progression_file = os.path.join(self.WorkDir, "Outputs", "Simulation_progress.txt")

    simulation_started = 0
    batch = 0
    uncertainty = -1
    multiplier = 1.0

    with open(progression_file, 'r') as fid:
      for line in fid:
        if "Simulation started (" in line:
          simulation_started = 0
          batch = 0
          uncertainty = -1
          multiplier = 1.0

        elif "batch " in line and " completed" in line:
          tmp = line.split(' ')
          if(tmp[1].isnumeric()): batch = int(tmp[1])
          if(len(tmp) >= 6): uncertainty = float(tmp[5])

        elif "10x more particles per batch" in line:
          multiplier *= 10.0

    NumParticles = int(batch * multiplier * self.NumProtons / 10.0)
    return NumParticles, uncertainty



  def init_simulation_directory(self):
    # Create simulation directory
    if not os.path.isdir(self.WorkDir):
      os.mkdir(self.WorkDir)

    # Clean output directory
    out_dir = os.path.join(self.WorkDir, "Outputs")
    if os.path.isdir(out_dir):
      file_list = os.listdir(out_dir)
      for file in file_list:

        if(file.endswith(".mhd")): os.remove(os.path.join(out_dir, file))
        if(file.endswith(".raw")): os.remove(os.path.join(out_dir, file))
        if(file.endswith(".txt")): os.remove(os.path.join(out_dir, file))
        if(file.endswith(".bin")): os.remove(os.path.join(out_dir, file))

        if(file == "tmp" and os.path.isdir(os.path.join(out_dir, file))):
          folder_path = os.path.join(self.WorkDir, "Outputs", "tmp")
          for root, dirs, files in os.walk(folder_path, topdown=False):
            for name in files: os.remove(os.path.join(root, name))
            for name in dirs: os.rmdir(os.path.join(root, name))


