import pydicom
import numpy as np
#from matplotlib.path import Path
from PIL import Image, ImageDraw

from Process.MHD_image import *

class RTstruct:

  def __init__(self):
    self.SeriesInstanceUID = ""
    self.PatientInfo = {}
    self.StudyInfo = {}
    self.CT_SeriesInstanceUID = ""
    self.DcmFile = ""
    self.isLoaded = 0
    self.Contours = []
    self.NumContours = 0
    
    
  def print_struct_info(self, prefix=""):
    print(prefix + "Struct: " + self.SeriesInstanceUID)
    print(prefix + "   " + self.DcmFile)
    
    
  def print_ROINames(self):
    print("\nRT Struct UID: " + self.SeriesInstanceUID)
    count = -1
    for contour in self.Contours:
      count += 1
      print('  [' + str(count) + ']  ' + contour.ROIName)
    
  
  
  def import_Dicom_struct(self, CT_list):
    if(self.isLoaded == 1):
      print("Warning: RTstruct " + self.SeriesInstanceUID + " is already loaded")
      return
      
    dcm = pydicom.dcmread(self.DcmFile)

    # find associated CT image
    CT = {}
    try:
      CT_UID = dcm.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[0].SeriesInstanceUID
      #FrameOfReferenceUID = dcm.ReferencedFrameOfReferenceSequence[0].FrameOfReferenceUID
      CT_ID = next((x for x, val in enumerate(CT_list) if val.SeriesInstanceUID == CT_UID), -1)
      CT = CT_list[CT_ID]
    except:
      pass

    if(CT == {}):
      print("Warning: Referenced CT image not found for RTstruct " + self.SeriesInstanceUID )
      print("RTstruct is imported on the first CT image instead.")
      CT = CT_list[0]

    self.CT_SeriesInstanceUID = CT.SeriesInstanceUID
    
    # load contours
    for dcm_struct in dcm.StructureSetROISequence:    
      ReferencedROI_id = next((x for x, val in enumerate(dcm.ROIContourSequence) if val.ReferencedROINumber == dcm_struct.ROINumber), -1)
      dcm_contour = dcm.ROIContourSequence[ReferencedROI_id]
    
      Contour = ROIcontour()
      Contour.SeriesInstanceUID = self.SeriesInstanceUID
      Contour.ROIName = dcm_struct.ROIName
      Contour.ROIDisplayColor = dcm_contour.ROIDisplayColor
    
      #print("Import contour " + str(len(self.Contours)) + ": " + Contour.ROIName)
    
      Contour.Mask = np.zeros((CT.GridSize[0], CT.GridSize[1], CT.GridSize[2]), dtype=np.bool)
      Contour.Mask_GridSize = CT.GridSize
      Contour.Mask_PixelSpacing = CT.PixelSpacing
      Contour.Mask_Offset = CT.ImagePositionPatient
      Contour.Mask_NumVoxels = CT.NumVoxels   
      Contour.ContourMask = np.zeros((CT.GridSize[0], CT.GridSize[1], CT.GridSize[2]), dtype=np.bool)
      
      SOPInstanceUID_match = 1

      if not hasattr(dcm_contour, 'ContourSequence'):
          print(Contour.ROIName + " has no attribute ContourSequence. Skip this structure...")
          continue

      for dcm_slice in dcm_contour.ContourSequence:
        Slice = {}
      
        # list of Dicom coordinates
        Slice["XY_dcm"] = list(zip( np.array(dcm_slice.ContourData[0::3]), np.array(dcm_slice.ContourData[1::3]) ))
        Slice["Z_dcm"] = float(dcm_slice.ContourData[2])
      
        # list of coordinates in the image frame
        Slice["XY_img"] = list(zip( ((np.array(dcm_slice.ContourData[0::3]) - CT.ImagePositionPatient[0]) / CT.PixelSpacing[0]), ((np.array(dcm_slice.ContourData[1::3]) - CT.ImagePositionPatient[1]) / CT.PixelSpacing[1]) ))
        Slice["Z_img"] = (Slice["Z_dcm"] - CT.ImagePositionPatient[2]) / CT.PixelSpacing[2]
        Slice["Slice_id"] = int(round(Slice["Z_img"]))
      
        # convert polygon to mask (based on matplotlib - slow)
        #x, y = np.meshgrid(np.arange(CT.GridSize[0]), np.arange(CT.GridSize[1]))
        #points = np.transpose((x.ravel(), y.ravel()))
        #path = Path(Slice["XY_img"])
        #mask = path.contains_points(points)
        #mask = mask.reshape((CT.GridSize[0], CT.GridSize[1]))
      
        # convert polygon to mask (based on PIL - fast)
        img = Image.new('L', (CT.GridSize[0], CT.GridSize[1]), 0)
        if(len(Slice["XY_img"]) > 1): ImageDraw.Draw(img).polygon(Slice["XY_img"], outline=1, fill=1)
        mask = np.array(img)
        Contour.Mask[:,:,Slice["Slice_id"]] = np.logical_or(Contour.Mask[:,:,Slice["Slice_id"]], mask)
        
        # do the same, but only keep contour in the mask
        img = Image.new('L', (CT.GridSize[0], CT.GridSize[1]), 0)
        if(len(Slice["XY_img"]) > 1): ImageDraw.Draw(img).polygon(Slice["XY_img"], outline=1, fill=0)
        mask = np.array(img)
        Contour.ContourMask[:,:,Slice["Slice_id"]] = np.logical_or(Contour.ContourMask[:,:,Slice["Slice_id"]], mask)
            
        Contour.ContourSequence.append(Slice)
      
        # check if the contour sequence is imported on the correct CT slice:
        if(hasattr(dcm_slice, 'ContourImageSequence') and CT.SOPInstanceUIDs[Slice["Slice_id"]] != dcm_slice.ContourImageSequence[0].ReferencedSOPInstanceUID):
          SOPInstanceUID_match = 0
      
      if SOPInstanceUID_match != 1:
        print("WARNING: some SOPInstanceUIDs don't match during importation of " + Contour.ROIName + " contour on CT image")
      
      #RGBA_color = list(Contour.ROIDisplayColor) + [255]
      #RGBA_color = np.array(RGBA_color).reshape(1,1,1,4)
      #Contour.ColorImage = Contour.ContourMask.reshape(CT.GridSize[0], CT.GridSize[1], CT.GridSize[2], 1) * RGBA_color
    
      self.Contours.append(Contour)
      self.NumContours += 1
      
    self.isLoaded = 1

      
      
class ROIcontour:

  def __init__(self):
    self.SeriesInstanceUID = ""
    self.ROIName = ""
    self.ContourSequence = []
    self.ROIDisplayColor = []
    self.Mask = []
    self.ContourMask = []
    self.Mask_GridSize = []
    self.Mask_PixelSpacing = []
    self.Mask_Offset = []
    self.Mask_NumVoxels = 0   
    
    
    
  def convert_to_MHD(self):
    mhd_image = MHD_image()
    mhd_image.ImagePositionPatient = self.Mask_Offset.copy()
    mhd_image.PixelSpacing = self.Mask_PixelSpacing.copy()
    mhd_image.GridSize = self.Mask_GridSize.copy()
    mhd_image.NumVoxels = self.Mask_NumVoxels
    mhd_image.Image = self.Mask.copy()
    
    return mhd_image
    
