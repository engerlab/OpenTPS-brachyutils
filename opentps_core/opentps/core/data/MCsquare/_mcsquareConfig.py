
__all__ = ['MCsquareConfig']


import os
import numpy as np


class MCsquareConfig:
  """
  Class to configure the MCsquare dose calculator. MCsquare is configured by a dictionary of key-value pairs.
  For the different parameters and their usage take a look at the ConfigTemplate.txt file in the opentps.core.data.MCsquare directory.
  """
  def __init__(self):
    ### Initialize MCsquare config with default values
    self.config = {}

    self.config["WorkDir"] = None
  
    # Simulation parameters
    self.config["Num_Threads"] = 0
    self.config["RNG_Seed"] = 0
    self.config["Num_Primaries"] = 1e7
    self.config["E_Cut_Pro"] = 0.5
    self.config["D_Max"] = 0.2
    self.config["Epsilon_Max"] = 0.25
    self.config["Te_Min"] = 0.05
  
    # Input files
    self.config["CT_File"] = None
    self.config["ScannerDirectory"] = None
    self.config["HU_Density_Conversion_File"] = None
    self.config["HU_Material_Conversion_File"] = None
    self.config["BDL_Machine_Parameter_File"] = None
    self.config["BDL_Plan_File"] = None
  
    # Physical parameters
    self.config["Simulate_Nuclear_Interactions"] = True
    self.config["Simulate_Secondary_Protons"] = True
    self.config["Simulate_Secondary_Deuterons"] = True
    self.config["Simulate_Secondary_Alphas"] = True
  
    # 4D simulation
    self.config["4D_Mode"] = False
    self.config["4D_Dose_Accumulation"] = False
    self.config["Field_type"] = "Velocity"
    self.config["Create_Ref_from_4DCT"] = False
    self.config["Create_4DCT_from_Ref"] = False
    self.config["Dynamic_delivery"] = False
    self.config["Breathing_period"] = 7.0
    self.config["CT_phases"] = 0
  
    # Robustness simulation
    self.config["Robustness_Mode"] = False
    self.config["Scenario_selection"] = "All"
    self.config["Simulate_nominal_plan"] = True
    self.config["Num_Random_Scenarios"] = 100
    self.config["Systematic_Setup_Error"] = [0.25, 0.25, 0.25]
    self.config["Random_Setup_Error"] = [0.1,  0.1,  0.1]
    self.config["Systematic_Range_Error"] = 3.0
    self.config["Systematic_Amplitude_Error"] = 5.0
    self.config["Random_Amplitude_Error"] = 5.0
    self.config["Systematic_Period_Error"] = 5.0
    self.config["Random_Period_Error"] = 5.0
  
    # Beamlet simulation
    self.config["Beamlet_Mode"] = False
    self.config["Beamlet_Parallelization"] = False
  
    # Beamlet simulation
    self.config["Optimization_Mode"] = False
  
    # Statistical noise and stopping criteria
    self.config["Compute_stat_uncertainty"] = True
    self.config["Stat_uncertainty"] = 0
    self.config["Ignore_low_density_voxels"] = True
    self.config["Export_batch_dose"] = False
    self.config["Max_Num_Primaries"] = 0
    self.config["Max_Simulation_time"] = 0
  
    # Output parameters
    self.config["Output_Directory"] = "Outputs"
    self.config["Energy_ASCII_Output"] = False
    self.config["Energy_MHD_Output"] = False
    self.config["Energy_Sparse_Output"] = False
    self.config["Dose_ASCII_Output"] = False
    self.config["Dose_MHD_Output"] = True
    self.config["Dose_Sparse_Output"] = False
    self.config["LET_ASCII_Output"] = False
    self.config["LET_MHD_Output"] = False
    self.config["LET_Sparse_Output"] = False
    self.config["Densities_Output"] = False
    self.config["Materials_Output"] = False
    self.config["Compute_DVH"] = False
    self.config["Dose_Sparse_Threshold"] = 0.0
    self.config["Energy_Sparse_Threshold"] = 0.0
    self.config["LET_Sparse_Threshold"] = 0.0
    self.config["Score_PromptGammas"] = False
    self.config["PG_LowEnergyCut"] = 0.0
    self.config["PG_HighEnergyCut"] = 50.0
    self.config["PG_Spectrum_NumBin"] = 150
    self.config["PG_Spectrum_Binning"] = 0.1
    self.config["LET_Calculation_Method"] = "StopPow"
    self.config["Export_Beam_dose"] = False
    self.config["Dose_to_Water_conversion"] = "Disabled"
    self.config["Dose_Segmentation"] = False
    self.config["Density_Threshold_for_Segmentation"] = 0.01
  
    # Independent scoring grid
    self.config["Independent_scoring_grid"] = False
    self.config["Scoring_origin"] = [0.0, 0.0, 0.0]
    self.config["Scoring_grid_size"] = [100, 100, 100]
    self.config["Scoring_voxel_spacing"] = [0.15, 0.15, 0.15]
    self.config["Dose_weighting_algorithm"] = "Volume"

  def __getitem__(self, key):
    return self.config[key]

  def __setitem__(self, key, value):
    self.config[key] = value

  def __str__(self):
    return self.mcsquareFormatted()

  def mcsquareFormatted(self) -> str:
    """
    Returns the configuration file in the format used by MCsquare

    Returns
    -------
    Template : str
        Configuration file in the format used by MCsquare
    """
    Module_folder = os.path.dirname(os.path.realpath(__file__))
    fid = open(os.path.join(Module_folder, "ConfigTemplate.txt"), 'r',encoding="utf-8")
    Template = fid.read()
    fid.close()

    for key in self.config:
      if np.ndim(self.config[key]) > 0: #i,e not a scalar #type(self.config[key]) == list:
        Template = Template.replace('{' + key.upper() + '}',
                                    str(self.config[key][0]) + " " + str(self.config[key][1]) + " " + str(self.config[key][2]))
      else:
        Template = Template.replace('{' + key.upper() + '}', str(self.config[key]))

    return Template
