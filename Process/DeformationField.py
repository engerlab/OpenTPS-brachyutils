import pydicom
import datetime
import numpy as np
import matplotlib.pyplot as plt
import scipy.ndimage

from Process.C_libraries.libInterp3_wrapper import *

class DeformationField:

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

    def import_Dicom_DF(self, CT_list):
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
            print("Warning: No CT image has been found with the same frame of reference as DeformationField " + self.SeriesInstanceUID )
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
        
        self.Image = df_image
        self.resample_to_CT_grid(CT)
        self.isLoaded = 1


    def euclidean_dist(self, v1, v2):
        return sum((p-q)**2 for p, q in zip(v1, v2)) ** .5


    def resample_to_CT_grid(self, CT):
        if(self.GridSize == CT.GridSize and self.euclidean_dist(self.ImagePositionPatient, CT.ImagePositionPatient) < 0.01 and self.euclidean_dist(self.PixelSpacing, CT.PixelSpacing) < 0.01):
            return
        else:
            print('Resample dose image to CT grid.')
            self.resample_image(CT.GridSize, CT.ImagePositionPatient, CT.PixelSpacing)
        

    def resample_image(self, GridSize, Offset, PixelSpacing):
        field_components = [0, 1, 2]
        # anti-aliasing filter
        if self.NumVoxels > np.product(GridSize): # downsampling
            sigma = [0, 0, 0]
            if(PixelSpacing[0] > self.PixelSpacing[0]): sigma[0] = 0.4 * (PixelSpacing[0]/self.PixelSpacing[0])
            if(PixelSpacing[1] > self.PixelSpacing[1]): sigma[1] = 0.4 * (PixelSpacing[1]/self.PixelSpacing[1])
            if(PixelSpacing[2] > self.PixelSpacing[2]): sigma[2] = 0.4 * (PixelSpacing[2]/self.PixelSpacing[2])
            if(sigma != [0, 0, 0]):
                print("Image is filtered before downsampling")

            img = np.zeros_like(self.Image)
            for i in field_components:
                img[:,:,:,i] = scipy.ndimage.gaussian_filter(self.Image[:,:,:,i], sigma)
            self.Image = img
        
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
            img_temp = Trilinear_Interpolation(self.Image[:,:,:,i], Init_GridSize, xi)
            img[:,:,:,i] = img_temp.reshape((GridSize[1], GridSize[0], GridSize[2])).transpose(1,0,2)
        self.Image = img
    
        self.ImagePositionPatient = list(Offset)
        self.PixelSpacing = list(PixelSpacing)
        self.GridSize = list(GridSize)
        self.NumVoxels = GridSize[0] * GridSize[1] * GridSize[2]
