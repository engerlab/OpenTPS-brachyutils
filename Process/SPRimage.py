import numpy as np
import scipy.interpolate
import math

from Process.MCsquare_CT_calibration import *
from Process.C_libraries.libRayTracing_wrapper import *


class SPRimage:

  def __init__(self):
    self.calibration = MCsquare_CT_calibration()
    self.Image = np.array([])
    
  
  
  def convert_CT_to_SPR(self, CT, Scanner):
    print("Convert CT image " + CT.ImgName + " to SPR using " + Scanner + " scanner calibration")
    self.calibration.load_calibration(Scanner)
    self.Image = np.interp(CT.Image, self.calibration.HU, self.calibration.SPR)
    self.ImagePositionPatient = CT.ImagePositionPatient
    self.PixelSpacing = CT.PixelSpacing
    self.GridSize = CT.GridSize
    self.NumVoxels = CT.NumVoxels


  def compute_WET_map(self, GantryAngle, CouchAngle, ROI=[]):
    if(self.Image == np.array([])):
      print("Error: SPR image not initialized.")

    # compute direction vector
    u,v,w = 1e-10, 1.0, 1e-10 # direction for gantry and couch at 0°
    [u,v,w] = Rotate_vector([u,v,w], math.radians(GantryAngle), 'z') # rotation for gantry angle
    [u,v,w] = Rotate_vector([u,v,w], math.radians(CouchAngle), 'y') # rotation for couch angle

    WET = WET_raytracing(self, [u,v,w], ROI)

    return WET
    
    
    
  def rangeToEnergy(self, r80):
    '''This function converts the water equivalent range (defined as r80,
    i.e., the position of the 80% dose in the distal falloff, in cm) to incident
    energy of the proton beam (in MeV).

    The formula comes from Loic Grevillot
    et al. [1, 2], from a fitting to the NIST/ICRU database.

    [1] L. Grevillot, et al. "A Monte Carlo pencil beam scanning model for
    proton treatment plan simulation using GATE/GEANT4."
    Phys Med Biol, 56(16):5203–5219, Aug 2011.
    [2] L. Grevillot, et al. "Optimization of geant4 settings for proton
    pencil beam scanning simulations using gate". Nuclear Instruments and
    Methods in Physics Research Section B: Beam Interactions
    with Materials and Atoms, 268(20):3295 – 3305, 2010.'''
    if r80<=0.:
        E0=0.
    else:
        E0 = math.exp(3.464048 + 0.561372013*math.log(r80) - 0.004900892*math.pow(math.log(r80),2) + 0.001684756748*math.pow(math.log(r80),3))

    return E0
  
  
  
  def energyToRange(self, E0):
    '''This function converts a proton beam energy (in MeV) to a water equivalent range (defined as r80,
    i.e., the position of the 80% dose in the distal falloff, in cm).

    The formula comes from Loic Grevillot
    et al. [1, 2], from a fitting to the NIST/ICRU database.

    [1] L. Grevillot, et al. "A Monte Carlo pencil beam scanning model for
    proton treatment plan simulation using GATE/GEANT4."
    Phys Med Biol, 56(16):5203–5219, Aug 2011.
    [2] L. Grevillot, et al. "Optimization of geant4 settings for proton
    pencil beam scanning simulations using gate". Nuclear Instruments and
    Methods in Physics Research Section B: Beam Interactions
    with Materials and Atoms, 268(20):3295 – 3305, 2010.'''
    if E0<=0.:
        r80=0.
    else:
        r80 = math.exp(-5.5064 + 1.2193*math.log(E0) + 0.15248*math.pow(math.log(E0),2) - 0.013296*math.pow(math.log(E0),3))

    return r80
    
    
  
  def get_voxel_index(self, position):
    id_x = math.floor((position[0] - self.ImagePositionPatient[0]) / self.PixelSpacing[0])
    id_y = math.floor((position[1] - self.ImagePositionPatient[1]) / self.PixelSpacing[1])
    id_z = math.floor((position[2] - self.ImagePositionPatient[2]) / self.PixelSpacing[2])
    return [id_x, id_y, id_z]
    
    
    
  def get_SPR_at_position(self, position):
    voxel_id = self.get_voxel_index(position)
    
    if(voxel_id[0] < 0 or voxel_id[1] < 0 or voxel_id[2] < 0): 
      return 0.001
      
    elif(voxel_id[0] >= self.GridSize[0] or voxel_id[1] >= self.GridSize[1] or voxel_id[2] >= self.GridSize[2]): 
      return 0.001
      
    else: 
      return self.Image[voxel_id[1], voxel_id[0], voxel_id[2]]
    
    # interpolation method here-below is much slower
    #x = self.ImagePositionPatient[0] + np.arange(self.GridSize[0]) * self.PixelSpacing[0]
    #y = self.ImagePositionPatient[1] + np.arange(self.GridSize[1]) * self.PixelSpacing[1]
    #z = self.ImagePositionPatient[2] + np.arange(self.GridSize[2]) * self.PixelSpacing[2]
    #SPR = scipy.interpolate.interpn((y,x,z), self.Image, (position[1], position[0], position[2]), method='linear', fill_value=0.001, bounds_error=False)[0]
    #return SPR
      
  

def Rotate_vector(vec, angle, axis):
  if axis == 'x':
    x = vec[0]
    y = vec[1] * math.cos(angle) - vec[2] * math.sin(angle)
    z = vec[1] * math.sin(angle) + vec[2] * math.cos(angle)
  elif axis ==  'y':
    x = vec[0] * math.cos(angle) + vec[2] * math.sin(angle)
    y = vec[1]
    z = -vec[0] * math.sin(angle) + vec[2] * math.cos(angle)
  elif axis == 'z':
    x = vec[0] * math.cos(angle) - vec[1] * math.sin(angle)
    y = vec[0] * math.sin(angle) + vec[1] * math.cos(angle)
    z = vec[2]

  return [x,y,z]
      
