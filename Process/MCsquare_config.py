import os

def export_MCsquare_config(config, FileName="config.txt"):


  file_path = os.path.join(config["WorkDir"], FileName)

  print("Write config file: " + file_path)

  Module_folder = os.path.dirname(os.path.realpath(__file__))
  fid = open(os.path.join(Module_folder, "ConfigTemplate.txt"), 'r')
  Template = fid.read()
  fid.close()

  for key in config:
    if type(config[key]) == list: Template = Template.replace('{' + key.upper() + '}', str(config[key][0]) + " " + str(config[key][1]) + " " + str(config[key][2]))
    else: Template = Template.replace('{' + key.upper() + '}', str(config[key]))

  fid = open(file_path, 'w')
  fid.write(Template)
  fid.close()



def generate_MCsquare_config(WorkDir, NumberOfPrimaries, Scanner_folder, BDL_file, CT_file="CT.mhd", Plan_file="PlanPencil.txt"):

  ### Initialize MCsquare config with default values
  config = {}
  config["WorkDir"] = WorkDir

  # Simulation parameters
  config["Num_Threads"] = 0
  config["RNG_Seed"] = 0
  config["Num_Primaries"] = NumberOfPrimaries
  config["E_Cut_Pro"] = 0.5
  config["D_Max"] = 0.2
  config["Epsilon_Max"] = 0.25
  config["Te_Min"] = 0.05

  # Input files
  config["CT_File"] = CT_file
  config["ScannerDirectory"] = os.path.abspath(Scanner_folder)
  config["HU_Density_Conversion_File"] = os.path.join(config["ScannerDirectory"], "HU_Density_Conversion.txt")
  config["HU_Material_Conversion_File"] = os.path.join(config["ScannerDirectory"], "HU_Material_Conversion.txt")
  config["BDL_Machine_Parameter_File"] = os.path.abspath(BDL_file)
  config["BDL_Plan_File"] = Plan_file

  # Physical parameters
  config["Simulate_Nuclear_Interactions"] = True
  config["Simulate_Secondary_Protons"] = True
  config["Simulate_Secondary_Deuterons"] = True
  config["Simulate_Secondary_Alphas"] = True

  # 4D simulation
  config["4D_Mode"] = False
  config["4D_Dose_Accumulation"] = False
  config["Field_type"] = "Velocity"
  config["Create_Ref_from_4DCT"] = False
  config["Create_4DCT_from_Ref"] = False
  config["Dynamic_delivery"] = False
  config["Breathing_period"] = 7.0
  config["CT_phases"] = 0

  # Robustness simulation
  config["Robustness_Mode"] = False
  config["Scenario_selection"] = "All"
  config["Simulate_nominal_plan"] = True
  config["Num_Random_Scenarios"] = 100
  config["Systematic_Setup_Error"] = [0.25, 0.25, 0.25]
  config["Random_Setup_Error"] = [0.1,  0.1,  0.1]
  config["Systematic_Range_Error"] = 3.0
  config["Systematic_Amplitude_Error"] = 5.0
  config["Random_Amplitude_Error"] = 5.0
  config["Systematic_Period_Error"] = 5.0
  config["Random_Period_Error"] = 5.0

  # Beamlet simulation
  config["Beamlet_Mode"] = False
  config["Beamlet_Parallelization"] = False

  # Beamlet simulation
  config["Optimization_Mode"] = False

  # Statistical noise and stopping criteria
  config["Compute_stat_uncertainty"] = True
  config["Stat_uncertainty"] = 0
  config["Ignore_low_density_voxels"] = True
  config["Export_batch_dose"] = False
  config["Max_Num_Primaries"] = 0
  config["Max_Simulation_time"] = 0

  # Output parameters
  config["Output_Directory"] = "Outputs"
  config["Energy_ASCII_Output"] = False
  config["Energy_MHD_Output"] = False
  config["Energy_Sparse_Output"] = False
  config["Dose_ASCII_Output"] = False
  config["Dose_MHD_Output"] = True
  config["Dose_Sparse_Output"] = False
  config["LET_ASCII_Output"] = False
  config["LET_MHD_Output"] = False
  config["LET_Sparse_Output"] = False
  config["Densities_Output"] = False
  config["Materials_Output"] = False
  config["Compute_DVH"] = False
  config["Dose_Sparse_Threshold"] = 0.0
  config["Energy_Sparse_Threshold"] = 0.0
  config["LET_Sparse_Threshold"] = 0.0
  config["Score_PromptGammas"] = False
  config["PG_LowEnergyCut"] = 0.0
  config["PG_HighEnergyCut"] = 50.0
  config["PG_Spectrum_NumBin"] = 150
  config["PG_Spectrum_Binning"] = 0.1
  config["LET_Calculation_Method"] = "StopPow"
  config["Export_Beam_dose"] = False
  config["Dose_to_Water_conversion"] = "Disabled"
  config["Dose_Segmentation"] = False
  config["Density_Threshold_for_Segmentation"] = 0.01

  # Independent scoring grid
  config["Independent_scoring_grid"] = False
  config["Scoring_origin"] = [0.0, 0.0, 0.0]
  config["Scoring_grid_size"] = [100, 100, 100]
  config["Scoring_voxel_spacing"] = [0.15, 0.15, 0.15]
  config["Dose_weighting_algorithm"] = "Volume"


  # Export configuration file
  #export_MCsquare_config(config)

  return config




