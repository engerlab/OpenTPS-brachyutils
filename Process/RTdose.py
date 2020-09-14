import pydicom
import datetime
import numpy as np
import scipy.interpolate
from matplotlib import cm

class RTdose:

  def __init__(self):
    self.SeriesInstanceUID = ""
    self.SOPInstanceUID = ""
    self.PatientInfo = {}
    self.StudyInfo = {}
    self.CT_SeriesInstanceUID = ""
    self.Plan_SOPInstanceUID = ""
    self.FrameOfReferenceUID = ""
    self.ImgName = ""
    self.DcmFile = ""
    self.isLoaded = 0
    
    
    
  def print_dose_info(self, prefix=""):
    print(prefix + "Dose: " + self.SOPInstanceUID)
    print(prefix + "   " + self.DcmFile)
    
    
    
  def import_Dicom_dose(self, CT):
    if(self.isLoaded == 1):
      print("Warning: Dose image " + self.SOPInstanceUID + " is already loaded")
      return
      
    dcm = pydicom.dcmread(self.DcmFile)
    
    self.CT_SeriesInstanceUID = CT.SeriesInstanceUID
    self.Plan_SOPInstanceUID = dcm.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID
    
    if(dcm.BitsStored == 16 and dcm.PixelRepresentation == 0):
      dt = np.dtype('uint16')
    elif(dcm.BitsStored == 16 and dcm.PixelRepresentation == 1):
      dt = np.dtype('int16')
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
    self.FrameOfReferenceUID = dcm.FrameOfReferenceUID
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
    
    
    
  def Initialize_from_MHD(self, ImgName, mhd_dose, CT, Plan):
      
    self.ImgName = ImgName
    self.PatientInfo = CT.PatientInfo
    self.StudyInfo = CT.StudyInfo
    self.CT_SeriesInstanceUID = CT.SeriesInstanceUID
    self.Plan_SOPInstanceUID = Plan.SOPInstanceUID
    self.FrameOfReferenceUID = CT.FrameOfReferenceUID
    self.SOPInstanceUID = pydicom.uid.generate_uid()
    self.SeriesInstanceUID = self.SOPInstanceUID + ".1"
    
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
    self.PatientInfo = CT.PatientInfo
    self.StudyInfo = CT.StudyInfo
    self.CT_SeriesInstanceUID = CT.SeriesInstanceUID
    self.FrameOfReferenceUID = CT.FrameOfReferenceUID
    self.SOPInstanceUID = pydicom.uid.generate_uid()
    self.SeriesInstanceUID = self.SOPInstanceUID + ".1"
    
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

    dose.SOPInstanceUID = pydicom.uid.generate_uid()
    dose.SeriesInstanceUID = self.SOPInstanceUID + ".1"
    dose.CT_SeriesInstanceUID = self.CT_SeriesInstanceUID
    dose.Plan_SOPInstanceUID = self.Plan_SOPInstanceUID
    dose.FrameOfReferenceUID = self.FrameOfReferenceUID

    dose.PatientInfo = self.PatientInfo
    dose.StudyInfo = self.StudyInfo
    
    dose.ImagePositionPatient = self.ImagePositionPatient
    dose.PixelSpacing = self.PixelSpacing
    dose.GridSize = self.GridSize
    dose.NumVoxels = self.NumVoxels
    
    dose.Image = self.Image.copy()
    
    dose.isLoaded = self.isLoaded

    return dose
        
        
  def export_Dicom(self, OutputFile, plan_uid=[]):

    # meta data
    meta = pydicom.dataset.FileMetaDataset()
    meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.481.2'
    meta.MediaStorageSOPInstanceUID = self.SOPInstanceUID
    #meta.ImplementationClassUID = '1.2.826.0.1.3680043.1.2.100.5.7.0.47' # from RayStation
    meta.ImplementationClassUID = '1.2.826.0.1.3680043.5.5.100.5.7.0.03' # modified
    #meta.FileMetaInformationGroupLength = 
    #meta.FileMetaInformationVersion = 

    # dicom dataset
    dcm_file = pydicom.dataset.FileDataset(OutputFile, {}, file_meta=meta, preamble=b"\0" * 128)
    dcm_file.SOPClassUID = meta.MediaStorageSOPClassUID
    dcm_file.SOPInstanceUID = self.SOPInstanceUID
    # dcm_file.ImplementationVersionName =
    # dcm_file.SpecificCharacterSet =
    # dcm_file.AccessionNumber = 
    # dcm_file.SoftwareVersion = 

    # patient information
    dcm_file.PatientName = self.PatientInfo.PatientName
    dcm_file.PatientID = self.PatientInfo.PatientID
    dcm_file.PatientBirthDate = self.PatientInfo.PatientBirthDate
    dcm_file.PatientSex = self.PatientInfo.PatientSex

    # content information
    dt = datetime.datetime.now()
    dcm_file.ContentDate = dt.strftime('%Y%m%d')
    dcm_file.ContentTime = dt.strftime('%H%M%S.%f')
    dcm_file.InstanceCreationDate = dt.strftime('%Y%m%d')
    dcm_file.InstanceCreationTime = dt.strftime('%H%M%S.%f')
    dcm_file.Modality = 'RTDOSE'
    dcm_file.Manufacturer = 'OpenMCsquare'
    dcm_file.ManufacturerModelName = 'OpenTPS'
    dcm_file.SeriesDescription = self.ImgName
    dcm_file.StudyInstanceUID = self.StudyInfo.StudyInstanceUID
    dcm_file.StudyID = self.StudyInfo.StudyID
    dcm_file.StudyDate = self.StudyInfo.StudyDate
    dcm_file.StudyTime = self.StudyInfo.StudyTime
    dcm_file.SeriesInstanceUID = self.SeriesInstanceUID
    dcm_file.SeriesNumber = 1
    dcm_file.InstanceNumber = 1
    dcm_file.PatientOrientation = ''
    dcm_file.FrameOfReferenceUID = self.FrameOfReferenceUID
    dcm_file.DoseUnits = 'GY'
    dcm_file.DoseType = 'PHYSICAL' # or 'EFFECTIVE' for RBE dose (but RayStation exports physical dose even if 1.1 factor is already taken into account)
    dcm_file.DoseSummationType = 'PLAN'
    ReferencedPlan = pydicom.dataset.Dataset()
    ReferencedPlan.ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.8" # ion plan
    if(plan_uid == []): ReferencedPlan.ReferencedSOPInstanceUID = self.Plan_SOPInstanceUID
    else: ReferencedPlan.ReferencedSOPInstanceUID = plan_uid
    dcm_file.ReferencedRTPlanSequence = pydicom.sequence.Sequence([ReferencedPlan])
    # dcm_file.ReferringPhysicianName
    # dcm_file.OperatorName

    # image information
    dcm_file.Width = self.GridSize[0]
    dcm_file.Columns = dcm_file.Width
    dcm_file.Height = self.GridSize[1]
    dcm_file.Rows = dcm_file.Height
    dcm_file.NumberOfFrames = self.GridSize[2]
    dcm_file.SliceThickness = self.PixelSpacing[2]
    dcm_file.PixelSpacing = self.PixelSpacing[0:2]
    dcm_file.ColorType: 'grayscale'
    dcm_file.ImagePositionPatient = self.ImagePositionPatient
    dcm_file.ImageOrientationPatient = [1, 0, 0, 0, 1, 0] # HeadFirstSupine=1,0,0,0,1,0  FeetFirstSupine=-1,0,0,0,1,0  HeadFirstProne=-1,0,0,0,-1,0  FeetFirstProne=1,0,0,0,-1,0
    dcm_file.SamplesPerPixel = 1
    dcm_file.PhotometricInterpretation = 'MONOCHROME2'
    dcm_file.FrameIncrementPointer = pydicom.tag.Tag((0x3004, 0x000c))
    dcm_file.GridFrameOffsetVector = list(np.arange(0, self.GridSize[2]*self.PixelSpacing[2], self.PixelSpacing[2]))

    # transfer syntax
    dcm_file.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    dcm_file.is_little_endian = True
    dcm_file.is_implicit_VR = False

    # image data
    dcm_file.BitDepth = 16
    dcm_file.BitsAllocated = 16
    dcm_file.BitsStored = 16
    dcm_file.HighBit = 15
    dcm_file.PixelRepresentation = 0 # 0=unsigned, 1=signed
    dcm_file.DoseGridScaling = self.Image.max()/(2**dcm_file.BitDepth - 1)
    dcm_file.PixelData = (self.Image/dcm_file.DoseGridScaling).astype(np.uint16).transpose(2,0,1).tostring()

    #print(dcm_file)

    # save dicom file
    print("Export dicom RTDOSE: " + OutputFile)
    dcm_file.save_as(OutputFile)


