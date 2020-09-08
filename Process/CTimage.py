import pydicom
import numpy as np

from Process.MHD_image import *

class CTimage:

  def __init__(self):
    self.SeriesInstanceUID = ""
    self.PatientInfo = {}
    self.StudyInfo = {}
    self.FrameOfReferenceUID = ""
    self.ImgName = ""
    self.DcmFiles = []
    self.isLoaded = 0
    
    
    
  def print_CT_info(self, prefix=""):
    print(prefix + "CT series: " + self.SeriesInstanceUID)
    for ct_slice in self.DcmFiles:
      print(prefix + "   " + ct_slice)
      
      
      
  def import_Dicom_CT(self):
    if(self.isLoaded == 1):
      print("Warning: CT serries " + self.SeriesInstanceUID + " is already loaded")
      return
  
    images = []
    SOPInstanceUIDs = []
    SliceLocation = np.zeros(len(self.DcmFiles), dtype='float')

    for i in range(len(self.DcmFiles)):
      file_path = self.DcmFiles[i]
      dcm = pydicom.dcmread(file_path)

      if(hasattr(dcm, 'SliceLocation') and abs(dcm.SliceLocation - dcm.ImagePositionPatient[2]) > 0.001):
        print("WARNING: SliceLocation (" + str(dcm.SliceLocation) + ") is different than ImagePositionPatient[2] (" + str(dcm.ImagePositionPatient[2]) + ") for " + file_path)

      SliceLocation[i] = float(dcm.ImagePositionPatient[2])
      images.append(dcm.pixel_array * dcm.RescaleSlope + dcm.RescaleIntercept)
      SOPInstanceUIDs.append(dcm.SOPInstanceUID)

    # sort slices according to their location in order to reconstruct the 3d image
    sort_index = np.argsort(SliceLocation)
    SliceLocation = SliceLocation[sort_index]
    SOPInstanceUIDs = [SOPInstanceUIDs[n] for n in sort_index]
    images = [images[n] for n in sort_index]
    Image = np.dstack(images).astype("float32")

    if Image.shape[0:2] != (dcm.Rows, dcm.Columns):
      print("WARNING: GridSize " + str(Image.shape[0:2]) + " different from Dicom Rows (" + str(dcm.Rows) + ") and Columns (" + str(dcm.Columns) + ")")

    MeanSliceDistance = (SliceLocation[-1] - SliceLocation[0]) / (len(images)-1)
    if(abs(MeanSliceDistance - dcm.SliceThickness) > 0.001):
      print("WARNING: MeanSliceDistance (" + str(MeanSliceDistance) + ") is different from SliceThickness (" + str(dcm.SliceThickness) + ")")

    self.FrameOfReferenceUID = dcm.FrameOfReferenceUID
    self.ImagePositionPatient = [float(dcm.ImagePositionPatient[0]), float(dcm.ImagePositionPatient[1]), SliceLocation[0]]
    self.PixelSpacing = [float(dcm.PixelSpacing[0]), float(dcm.PixelSpacing[1]), MeanSliceDistance]
    self.GridSize = list(Image.shape)
    self.NumVoxels = self.GridSize[0] * self.GridSize[1] * self.GridSize[2]
    self.Image = Image
    self.SOPInstanceUIDs = SOPInstanceUIDs
    self.VoxelX = self.ImagePositionPatient[0] + np.arange(self.GridSize[0])*self.PixelSpacing[0]
    self.VoxelY = self.ImagePositionPatient[1] + np.arange(self.GridSize[1])*self.PixelSpacing[1]
    self.VoxelZ = self.ImagePositionPatient[2] + np.arange(self.GridSize[2])*self.PixelSpacing[2]
    self.isLoaded = 1
    
   
  
  def convert_to_MHD(self):
    mhd_image = MHD_image()
    mhd_image.ImagePositionPatient = self.ImagePositionPatient.copy()
    mhd_image.PixelSpacing = self.PixelSpacing.copy()
    mhd_image.GridSize = self.GridSize.copy()
    mhd_image.NumVoxels = self.NumVoxels
    mhd_image.Image = self.Image.copy()
    
    return mhd_image
    
    
    
  def prepare_image_for_viewer(self):
    img_min = self.Image.min()
    #img_max = self.Image.max()
    img_max = np.percentile(self.Image, 99.995)
    img = 255 * (self.Image - img_min) / (img_max - img_min) # normalize data betwee, 0 and 255
    img[img>255] = 255
    return img
    
