import os
import numpy as np


class MCsquare_BDL:

  def __init__(self):
    self.Path_MCsquareLib = os.path.abspath("./MCsquare")
    self.BDL_folder = os.path.join(self.Path_MCsquareLib, "BDL")
    self.list = self.get_list_BDL()
    self.selected_BDL = self.list[0]
    self.isLoaded = 0
    self.NominalEnergy = []
    self.MeanEnergy = []
    self.EnergySpread = []
    self.ProtonsMU = []
    self.Weight1 = []
    self.SpotSize1x = []
    self.Divergence1x = []
    self.Correlation1x = []
    self.SpotSize1y = []
    self.Divergence1y = []
    self.Correlation1y = []
    self.Weight2 = []
    self.SpotSize2x = []
    self.Divergence2x = []
    self.Correlation2x = []
    self.SpotSize2y = []
    self.Divergence2y = []
    self.Correlation2y = []
    self.RangeShifters = []
    
    

  def get_list_BDL(self):
    BDL_list = []
    
    file_list = os.listdir(self.BDL_folder)
    
    for file_name in file_list:
      if(file_name[-4:] == ".txt"): BDL_list.append(file_name[0:-4])
    
    return tuple(BDL_list)
    
    
    
  def MU_to_NumProtons(self, MU, energy):
    # Constant which depends on the mean energy loss (W) to create an electron/hole pair
    K = 35.87 # in eV (other value 34.23 ?)
  
    # Air stopping power (fit ICRU) multiplied by air density
    SP = (9.6139e-9*energy**4 - 7.0508e-6*energy**3 + 2.0028e-3*energy**2 - 2.7615e-1*energy + 2.0082e1) * 1.20479E-3 * 1E6 # in eV / cm

    # Temp & Pressure correction
    PTP = 1.0 

    # MU calibration (1 MU = 3 nC/cm)
    # 1cm of effective gap
    C = 3.0E-9 # in C / cm

    # Gain: 1eV = 1.602176E-19 J
    Gain = (C*K) / (SP*PTP*1.602176E-19)

    return MU*Gain

    # Loic's formula
    #K=37.60933;
    #SP= 9.6139e-9*energy^4 - 7.0508e-6*energy^3 + 2.0028e-3*energy^2 - 2.7615e-1*energy + 2.0082e1;
    #PTP=1;
    #Gain=3./(K*SP*PTP*1.602176E-10);
    #NumProtons = weight*Gain;



  def get_path(self):
    return os.path.join(self.BDL_folder, self.selected_BDL + ".txt")



  def import_BDL(self, selected_BDL=""):
    if(selected_BDL != ""): self.selected_BDL = selected_BDL
    
    path = self.get_path()
    with open(path, 'r') as fid:
      
      # verify BDL format
      line = fid.readline()
      fid.seek(0)
      if not "--UPenn beam model (double gaussian)--" in line and not "--Lookup table BDL format--" in line:
        print("ERROR: BDL format not supported")
        fid.close()
        return None
      
      line_num = 0
      for line in fid:
        line_num += 1

        # remove comments
        if line[0] == '#': continue
        line = line.split('#')[0]

        # find begining of the BDL table in the file
        if("NominalEnergy" in line): table_line = line_num+1

        # parse range shifter data
        if("Range Shifter parameters" in line):
          RS = RangeShifter_data()
          self.RangeShifters.append(RS)

        if("RS_ID" in line):
          line = line.split('=')
          value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
          self.RangeShifters[-1].ID = value
          
        if("RS_type" in line):
          line = line.split('=')
          value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
          self.RangeShifters[-1].type = value.lower()
          
        if("RS_material" in line):
          line = line.split('=')
          value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
          self.RangeShifters[-1].material = int(value)
          
        if("RS_density" in line):
          line = line.split('=')
          value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
          self.RangeShifters[-1].density = float(value)
          
        if("RS_WET" in line):
          line = line.split('=')
          value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
          self.RangeShifters[-1].WET = float(value)

    
    # parse BDL table
    BDL_table = np.loadtxt(path, skiprows=table_line)
  
    self.NominalEnergy = BDL_table[:,0]
    self.MeanEnergy = BDL_table[:,1]
    self.EnergySpread = BDL_table[:,2]
    self.ProtonsMU = BDL_table[:,3]
    self.Weight1 = BDL_table[:,4]
    self.SpotSize1x = BDL_table[:,5]
    self.Divergence1x = BDL_table[:,6]
    self.Correlation1x = BDL_table[:,7]
    self.SpotSize1y = BDL_table[:,8]
    self.Divergence1y = BDL_table[:,9]
    self.Correlation1y = BDL_table[:,10]
    self.Weight2 = BDL_table[:,11]
    self.SpotSize2x = BDL_table[:,12]
    self.Divergence2x = BDL_table[:,13]
    self.Correlation2x = BDL_table[:,14]
    self.SpotSize2y = BDL_table[:,15]
    self.Divergence2y = BDL_table[:,16]
    self.Correlation2y = BDL_table[:,17]
      
    self.isLoaded = 1
    
    
    
class RangeShifter_data:

  def __init__(self):
    self.ID = ''
    self.type = ''
    self.material = -1
    self.density = 0.0
    self.WET = 0.0

  def print_info(self):
    print(' ')
    print('RS_ID = ' + self.ID)
    print('RS_type = ' + self.type)
    print('RS_material = ' + str(self.material))
    print('RS_density = ' + str(self.density))
    print('RS_WET = ' + str(self.WET))
    print(' ')