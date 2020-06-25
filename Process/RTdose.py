import pydicom
import numpy as np
import scipy.interpolate
from matplotlib import cm

class RTdose:

  def __init__(self):
    self.SeriesInstanceUID = ""
    self.CT_SeriesInstanceUID = ""
    self.ImgName = ""
    self.DcmFile = ""
    self.isLoaded = 0
    
    
    
  def print_dose_info(self, prefix=""):
    print(prefix + "Dose: " + self.SeriesInstanceUID)
    print(prefix + "   " + self.DcmFile)
    
    
    
  def import_Dicom_dose(self, CT):
    if(self.isLoaded == 1):
      print("Warning: Dose image " + self.SeriesInstanceUID + " is already loaded")
      return
      
    dcm = pydicom.dcmread(self.DcmFile)
    
    self.CT_SeriesInstanceUID = CT.SeriesInstanceUID
    
    if(dcm.PixelRepresentation != 0): 
      print("Error: Unknown PixelRepresentation for " + self.DcmFile)
      return
    
    if(dcm.BitsStored == 16):
      dt = np.dtype('uint16')
    else:
      print("Error: Unknown data type for " + self.DcmFile)
      return
      
    if(dcm.HighBit == dcm.BitsStored-1):
      dt = dt.newbyteorder('L')
    else:
      dt = dt.newbyteorder('B')
      
    dose_image = np.frombuffer(dcm.PixelData, dtype=dt) 
    dose_image = dose_image.reshape((dcm.Columns, dcm.Rows, dcm.NumberOfFrames), order='F').transpose(1,0,2)
    dose_image = dose_image * dcm.DoseGridScaling
    
    self.Image = dose_image
    self.ImagePositionPatient = dcm.ImagePositionPatient
    self.PixelSpacing = [dcm.PixelSpacing[0], dcm.PixelSpacing[1], dcm.SliceThickness]
    self.GridSize = [dcm.Columns, dcm.Rows, dcm.NumberOfFrames]
    self.NumVoxels = self.GridSize[0] * self.GridSize[1] * self.GridSize[2]
    
    if hasattr(dcm, 'GridFrameOffsetVector'):
      if(dcm.GridFrameOffsetVector[1] - dcm.GridFrameOffsetVector[0] < 0):
        self.Image = np.flip(self.Image, 2)
        self.ImagePositionPatient[2] = self.ImagePositionPatient[2] - self.GridSize[2]*self.PixelSpacing[2]
    
    self.resample_to_CT_grid(CT)
    self.isLoaded = 1
    
   
  
  def prepare_image_for_viewer(self):
    #img_min = self.Image.min()
    img_min = 0.05
    #img_max = self.Image.max()
    img_max = np.percentile(self.Image, 99.995) # reduce impact of noise on the dose range calculation
    img_data = 255 * (self.Image - img_min) / (img_max - img_min) # normalize data betwee, 0 and 255
    color_index = np.arange(255)
    rgb = cm.get_cmap('jet')(color_index) * 255 # generate colormap
    img_viewer = np.zeros((self.GridSize[0], self.GridSize[1], self.GridSize[2], 4))
    img_viewer[:,:,:,0] = np.interp(img_data, color_index, rgb[:,2]) # apply colormap for each channel
    img_viewer[:,:,:,1] = np.interp(img_data, color_index, rgb[:,1])
    img_viewer[:,:,:,2] = np.interp(img_data, color_index, rgb[:,0])
    img_viewer[:,:,:,3] = 255 * (img_data > img_min)
    
    return img_viewer
    
    
    
  def Initialize_from_MHD(self, ImgName, mhd_dose, CT):
      
    self.ImgName = ImgName
    self.CT_SeriesInstanceUID = CT.SeriesInstanceUID
    self.SeriesInstanceUID = pydicom.uid.generate_uid()
    
    self.ImagePositionPatient = mhd_dose.ImagePositionPatient
    self.PixelSpacing = mhd_dose.PixelSpacing
    self.GridSize = mhd_dose.GridSize
    self.NumVoxels = mhd_dose.NumVoxels
    
    self.Image = mhd_dose.Image
    self.resample_to_CT_grid(CT)
    
    self.isLoaded = 1
    
    return self
    
    
    
  def Initialize_from_beamlet_dose(self, ImgName, beamlets, dose_vector, CT):
      
    self.ImgName = ImgName
    self.CT_SeriesInstanceUID = CT.SeriesInstanceUID
    self.SeriesInstanceUID = pydicom.uid.generate_uid()
    
    self.ImagePositionPatient = beamlets.Offset
    self.PixelSpacing = beamlets.VoxelSpacing
    self.GridSize = beamlets.ImageSize
    self.NumVoxels = beamlets.NbrVoxels
    
    self.Image = np.reshape(dose_vector, self.GridSize, order='F')
    self.Image = np.flip(self.Image, (0,1)).transpose(1,0,2)
    self.resample_to_CT_grid(CT)
    
    self.isLoaded = 1
    
    return self
    
    
  
  def euclidean_dist(self, v1, v2):
    return sum((p-q)**2 for p, q in zip(v1, v2)) ** .5
    
    
      
  def resample_to_CT_grid(self, CT):
    if(self.GridSize == CT.GridSize and self.euclidean_dist(self.ImagePositionPatient, CT.ImagePositionPatient) < 0.001 and self.euclidean_dist(self.PixelSpacing, CT.PixelSpacing) < 0.001):
      return
    else:
      print('Resample dose image to CT grid.')
    
      x = self.ImagePositionPatient[1] + np.arange(self.GridSize[1]) * self.PixelSpacing[1]
      y = self.ImagePositionPatient[0] + np.arange(self.GridSize[0]) * self.PixelSpacing[0]
      z = self.ImagePositionPatient[2] + np.arange(self.GridSize[2]) * self.PixelSpacing[2]
  
      xi = np.array(np.meshgrid(CT.VoxelY, CT.VoxelX, CT.VoxelZ))
      xi = np.rollaxis(xi, 0, 4)
      xi = xi.reshape((xi.size // 3, 3))
  
      self.Image = scipy.interpolate.interpn((x,y,z), self.Image, xi, method='linear', fill_value=0, bounds_error=False)
      self.Image = self.Image.reshape((CT.GridSize[0], CT.GridSize[1], CT.GridSize[2])).transpose(1,0,2)
  
      self.ImagePositionPatient = CT.ImagePositionPatient
      self.PixelSpacing = CT.PixelSpacing
      self.GridSize = CT.GridSize
      self.NumVoxels = CT.NumVoxels



  def copy(self):
    dose = RTdose()

    dose.ImgName = self.ImgName
    dose.CT_SeriesInstanceUID = self.CT_SeriesInstanceUID
    dose.SeriesInstanceUID = pydicom.uid.generate_uid()
    
    dose.ImagePositionPatient = self.ImagePositionPatient
    dose.PixelSpacing = self.PixelSpacing
    dose.GridSize = self.GridSize
    dose.NumVoxels = self.NumVoxels
    
    dose.Image = self.Image.copy()
    
    dose.isLoaded = self.isLoaded

    return dose
        
        
