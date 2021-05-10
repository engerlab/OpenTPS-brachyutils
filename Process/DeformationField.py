import pydicom
import datetime
import numpy as np
import matplotlib.pyplot as plt
import scipy.ndimage
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
    self.isLoaded = 0


  def Init_Field_Zeros(self, GridSize, Offset=[0, 0, 0], PixelSpacing=[1, 1, 1]):
    if(len(GridSize) == 3): GridSize = tuple(GridSize) + (3,)
    elif(len(GridSize) == 4 and GridSize[3] != 3): 
      print("Error: last dimension of deformation field should be of size 3")
      return

    self.Velocity = np.zeros(GridSize)
    self.ImagePositionPatient = Offset
    self.PixelSpacing = PixelSpacing
    self.GridSize = GridSize[0:3]



  def import_Dicom_DF(self, CT_list, df_type='Velocity'):
    if(self.isLoaded == 1):
      print("Warning: Deformation Field " + self.SOPInstanceUID + " is already loaded")
      return
  
    dcm = pydicom.dcmread(self.DcmFile).DeformableRegistrationSequence[0]
        
    # find associated CT image
    CT = {}
    try:
      CT_ID = next((x for x, val in enumerate(CT_list) if val.FrameOfReferenceUID == dcm.SourceFrameOfReferenceUID), -1)
      CT_ID = next((x for x, val in enumerate(CT_list) if val.FrameOfReferenceUID == dcm.FrameOfReferenceUID), -1)
      CT = CT_list[CT_ID]
    except:
      pass

    if(CT == {}):
      print("Warning: No CT image has been found with the same frame of reference as DeformationField " )
      print("DeformationField is imported on the first CT image.")
      CT = CT_list[0]

    # import deformation field
    self.CT_SeriesInstanceUID = CT.SeriesInstanceUID
    self.FrameOfReferenceUID = dcm.SourceFrameOfReferenceUID
    def0 = dcm.DeformableRegistrationGridSequence[0]

    df_image = np.frombuffer(def0.VectorGridData, dtype=np.float32) 
    # Deformation field coming from REGGUI
    df_image = df_image.reshape((3, def0.GridDimensions[0], def0.GridDimensions[1], def0.GridDimensions[2]), order='F').transpose(1,2,3,0)

    self.ImagePositionPatient = def0.ImagePositionPatient
    self.ImageOrientationPatient = def0.ImageOrientationPatient
    self.GridSize = def0.GridDimensions
    self.PixelSpacing = def0.GridResolution
    self.NumVoxels = self.GridSize[0] * self.GridSize[1] * self.GridSize[2]
    
    if df_type=='Velocity':
      self.Velocity = df_image
      self.Displacement = self.Exponentiation()
      # Resample both the velocity and diplacement to the CT
      self.resample_to_CT_grid(CT, which_df='both')
    elif df_type=='Displacement':
      self.Displacement = df_image
      self.resample_to_CT_grid(CT, which_df='Displacement')
    else:
      print("Unknown deformation field type")
      return
    self.isLoaded = 1


  def euclidean_dist(self, v1, v2):
    return sum((p-q)**2 for p, q in zip(v1, v2)) ** .5


  def resample_to_CT_grid(self, CT, which_df):
    if(self.GridSize == CT.GridSize and self.euclidean_dist(self.ImagePositionPatient, CT.ImagePositionPatient) < 0.01 and self.euclidean_dist(self.PixelSpacing, CT.PixelSpacing) < 0.01):
      return
    else:
      print('Resample dose image to CT grid.')
      self.resample_DF(CT.GridSize, CT.ImagePositionPatient, CT.PixelSpacing, which_df)
      

  def resample_DF(self, GridSize, Offset, PixelSpacing, which_df='both'):
    if which_df == 'both':
      assert self.Velocity != []
      assert self.Displacement != []
      self.Velocity = self.resample_image(self.Velocity, GridSize, Offset, PixelSpacing)
      self.Displacement = self.resample_image(self.Displacement, GridSize, Offset, PixelSpacing)
    elif which_df == 'Velocity':
      assert self.Velocity != []
      self.Velocity = self.resample_image(self.Velocity, GridSize, Offset, PixelSpacing)
    elif which_df == 'Displacement':
      assert self.Displacement != []
      self.Displacement = self.resample_image(self.Displacement, GridSize, Offset, PixelSpacing)
    else:
      print("parameter which_df should either be 'both', 'Velocity' or 'Displacement'.")
      return

    self.ImagePositionPatient = list(Offset)
    self.PixelSpacing = list(PixelSpacing)
    self.GridSize = list(GridSize)
    self.NumVoxels = GridSize[0] * GridSize[1] * GridSize[2]


  def resample_image(self, img_to_resample, GridSize, Offset, PixelSpacing):
    field_components = [0, 1, 2]
    # anti-aliasing filter
    if self.NumVoxels > np.product(GridSize): # downsampling
      sigma = [0, 0, 0]
      if(PixelSpacing[0] > self.PixelSpacing[0]): sigma[0] = 0.4 * (PixelSpacing[0]/self.PixelSpacing[0])
      if(PixelSpacing[1] > self.PixelSpacing[1]): sigma[1] = 0.4 * (PixelSpacing[1]/self.PixelSpacing[1])
      if(PixelSpacing[2] > self.PixelSpacing[2]): sigma[2] = 0.4 * (PixelSpacing[2]/self.PixelSpacing[2])
      if(sigma != [0, 0, 0]):
          print("Image is filtered before downsampling")

      img = np.zeros_like(img_to_resample)
      for i in field_components:
        img[:,:,:,i] = scipy.ndimage.gaussian_filter(img_to_resample[:,:,:,i], sigma)
      img_to_resample = img
    
    # resampling    
    Init_GridSize = list(self.GridSize)

    interp_x = (Offset[0] - self.ImagePositionPatient[0] + np.arange(GridSize[1])*PixelSpacing[0]) / self.PixelSpacing[0]
    interp_y = (Offset[1] - self.ImagePositionPatient[1] + np.arange(GridSize[0])*PixelSpacing[1]) / self.PixelSpacing[1]
    interp_z = (Offset[2] - self.ImagePositionPatient[2] + np.arange(GridSize[2])*PixelSpacing[2]) / self.PixelSpacing[2]

    xi = np.array(np.meshgrid(interp_y, interp_x, interp_z))
    xi = np.rollaxis(xi, 0, 4)
    xi = xi.reshape((xi.size // 3, 3))

    img = np.zeros((*GridSize,3))
    for i in field_components:
      img_temp = Trilinear_Interpolation(img_to_resample[:,:,:,i], Init_GridSize, xi)
      img[:,:,:,i] = img_temp.reshape((GridSize[1], GridSize[0], GridSize[2])).transpose(1,0,2)
    return img



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
    deformed = deformed.reshape((self.GridSize[1], self.GridSize[0], self.GridSize[2])).transpose(1,0,2)

    return deformed
