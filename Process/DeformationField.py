import math
import numpy as np
from scipy.ndimage import gaussian_filter

from Process.C_libraries.libInterp3_wrapper import *

class DeformationField:

  def __init__(self):
    self.FieldName = ""
    self.ImagePositionPatient = [0, 0, 0]
    self.PixelSpacing = [1, 1, 1]
    self.GridSize = [0, 0, 0]
    self.NumVoxels = 0
    self.Velocity = []
    self.Displacement = []



  def Init_Field_Zeros(self, GridSize, Offset=[0, 0, 0], PixelSpacing=[1, 1, 1]):
    if(len(GridSize) == 3): GridSize = tuple(GridSize) + (3,)
    elif(len(GridSize) == 4 and GridSize[3] != 3): 
      print("Error: last dimension of deformation field should be of size 3")
      return

    self.Velocity = np.zeros(GridSize)
    self.ImagePositionPatient = Offset
    self.PixelSpacing = PixelSpacing
    self.GridSize = GridSize[0:3]



  def Exponentiation(self, save_displacement=0):
    norm = np.square(self.Velocity[:,:,:,0])+np.square(self.Velocity[:,:,:,1])+np.square(self.Velocity[:,:,:,2])
    N = math.ceil(2 + math.log2(np.amax(np.sqrt(norm)))/2) +1;
    if N<1: N=1
    print("Field exponentiation (N=" + str(N) + ')')

    self.Displacement = self.Velocity.copy() * 2**(-N)

    for r in range(N):
      new_0 = self.apply_deformation(self.Displacement[:,:,:,0], fill_value=0)
      new_1 = self.apply_deformation(self.Displacement[:,:,:,1], fill_value=0)
      new_2 = self.apply_deformation(self.Displacement[:,:,:,2], fill_value=0)
      self.Displacement[:,:,:,0] += new_0
      self.Displacement[:,:,:,1] += new_1
      self.Displacement[:,:,:,2] += new_2

    output = self.Displacement
    if(save_displacement == 0): self.Displacement = []

    return output




  def apply_deformation(self, img, fill_value=-1000):
    size = img.shape

    if(tuple(self.GridSize) != size):
      print("Error: image dimensions must match with the vector field to apply the deformation.")
      return

    if(self.Displacement == []):
      field = self.Exponentiation()
    else:
      field = self.Displacement

    x = np.arange(size[0])
    y = np.arange(size[1])
    z = np.arange(size[2])
    xi = np.array(np.meshgrid(x, y, z))
    xi = np.rollaxis(xi, 0, 4)
    xi = xi.reshape((xi.size // 3, 3))
    xi = xi.astype('float32')
    xi[:,0] += field[:,:,:,0].transpose(1,0,2).reshape((xi.shape[0],))
    xi[:,1] += field[:,:,:,1].transpose(1,0,2).reshape((xi.shape[0],))
    xi[:,2] += field[:,:,:,2].transpose(1,0,2).reshape((xi.shape[0],))
    #deformed = scipy.interpolate.interpn((x,y,z), img, xi, method='linear', fill_value=fill_value, bounds_error=False)
    deformed = Trilinear_Interpolation(img, size, xi, fill_value=fill_value)
    deformed = deformed.reshape(size).transpose(1,0,2)

    return deformed