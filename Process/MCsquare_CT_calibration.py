import os
import re
import numpy as np

class MCsquare_CT_calibration:

  def __init__(self):
    self.Path_MCsquareLib = os.path.abspath("./MCsquare")
    self.Scanner_folder = os.path.join(self.Path_MCsquareLib, "Scanners")
    self.Materials_folder = os.path.join(self.Path_MCsquareLib, "Materials")
    self.list = self.get_list_Scanners()
    self.selected_Scanner = self.list[0]
    
    # calibration data
    self.HU = np.array([])
    self.mass_densities = np.array([])
    self.material_labels = np.array([])
    self.SPR = np.array([])
    self.RelElecDensities = np.array([])
    


  def get_path(self):
    return os.path.join(self.Scanner_folder, self.selected_Scanner)
    
    
    
  def load_calibration(self, scanner):
    if(scanner in self.list): self.selected_Scanner = scanner
    else:
      print("Error: " + scanner + " folder not found in " + self.Scanner_folder)
      return
    
    path = self.get_path()
    
    # Load Files
    HU_Density_File = np.loadtxt(os.path.join(path, "HU_Density_Conversion.txt"),'float')
    HU_Material_File = np.loadtxt(os.path.join(path, "HU_Material_Conversion.txt"),'float')

    # Import scanner calibration data
    HU_Density_Data, Density_Data = HU_Density_File[:,0], HU_Density_File[:,1]
    HU_Material_Data, Material_Data = HU_Material_File[:,0], HU_Material_File[:,1].astype(int)

    # Find the density and material corresponding to each HU
    HU_merged = np.concatenate((HU_Density_Data , HU_Material_Data))
    self.HU = np.unique(HU_merged)
    self.mass_densities = np.interp(self.HU, HU_Density_Data, Density_Data)
    self.material_labels = np.full(len(self.HU), Material_Data[0])
    for i,j in zip(HU_Material_Data, Material_Data):
        self.material_labels[self.HU >= i] = j

    # Import the list of materials
    Material_File = np.loadtxt(os.path.join(self.Materials_folder, "list.dat"), 'str')
    Material_index,Material_name = Material_File[:,0].astype(int),Material_File[:,1]

    # Import water electron density and stopping powers (SP) at 100 MeV
    Water_SP = self.import_SP_data(os.path.join(self.Materials_folder,'Water','G4_Stop_Pow.dat'))
    Water_ElecDensity = self.import_ElecDensity(os.path.join(self.Materials_folder, 'Water', 'Material_Properties.dat'))

    # Compute SPR corresponding to each HU
    self.SPR = np.empty(len(self.HU))
    self.RelElecDensities = np.empty(len(self.HU))

    for i in range(len(self.HU)):
        index = np.where(Material_index == self.material_labels[i])
        Name = Material_name[index]
        SP = self.import_SP_data(os.path.join(self.Materials_folder, Name[0], 'G4_Stop_Pow.dat'))
        self.SPR[i] = (self.mass_densities[i] * SP / Water_SP)
        ElecDensity = self.import_ElecDensity(os.path.join(self.Materials_folder, Name[0], 'Material_Properties.dat'))
        self.RelElecDensities[i] = (self.mass_densities[i] * ElecDensity / Water_ElecDensity)



  def import_SP_data(self, FileName):
    data = np.loadtxt(FileName,'float')
    SP = np.interp(100.0,data[:,0],data[:,1])
    return SP
    
    
    
  def import_ElecDensity(self, FileName):
    with open(FileName,"r") as f:
      for line in f:
        if re.search(r'Electron_Density',line):
          line=line.split()
          ElecDensity = float(line[1])
          return ElecDensity
                
    
    
  def get_list_Scanners(self):
    Scanner_list = []
    
    dir_list = os.listdir(self.Scanner_folder)
    
    for dir_name in dir_list:
      if os.path.isdir(os.path.join(self.Scanner_folder, dir_name)): Scanner_list.append(dir_name)
    
    return tuple(Scanner_list)
