
import numpy as np
import scipy.optimize
import scipy.ndimage

from Process.DeformationField import *


class Registration:

  def __init__(self, Fixed=[], Moving=[]):
    self.Fixed = Fixed
    self.Moving = Moving
    self.Deformed = []
    self.ROI_box = []



  def Registration_demons(self, Niter=15):
    # Resample moving image
    if(not self.Fixed.is_same_grid(self.Moving)):
      self.Moving = self.Resample_moving_image()

    # Initialization
    Grad_fixed = np.gradient(self.Fixed.Image)
    deformed = self.Moving.Image.copy()
    field = DeformationField()
    field.Init_Field_Zeros(deformed.shape)
    
    # Iterative loop
    for i in range(Niter):
      SSD = self.Compute_SSD(self.Fixed.Image, deformed)
      print('Iteration ' + str(i+1) + ': SSD=' + str(SSD))
      Grad_moving = np.gradient(deformed)
      squared_diff = np.square(self.Fixed.Image-deformed)
      squared_norm_grad = np.square(Grad_fixed[0]+Grad_moving[0])+np.square(Grad_fixed[1]+Grad_moving[1])+np.square(Grad_fixed[2]+Grad_moving[2])

      # demons formula
      field.Velocity[:,:,:,0] += 2 * (self.Fixed.Image - deformed) * (Grad_fixed[0]+Grad_moving[0]) / (squared_diff + squared_norm_grad + 1e-5)
      field.Velocity[:,:,:,1] += 2 * (self.Fixed.Image - deformed) * (Grad_fixed[1]+Grad_moving[1]) / (squared_diff + squared_norm_grad + 1e-5)
      field.Velocity[:,:,:,2] += 2 * (self.Fixed.Image - deformed) * (Grad_fixed[2]+Grad_moving[2]) / (squared_diff + squared_norm_grad + 1e-5)

      # regularization (Gaussian filter)
      self.Regularization(field, filter="Gaussian", sigma=1.0)

      # deformation  
      # velocity field converted to displacement field before applying the deformation
      deformed = field.apply_deformation(self.Moving.Image) 

    self.Deformed = self.Moving.copy()
    self.Deformed.Image = deformed

    return field



  def Regularization(self, field, filter="Gaussian", sigma=1.0):

    if(filter == "Gaussian"):
      field.Velocity[:,:,:,0] = scipy.ndimage.gaussian_filter(field.Velocity[:,:,:,0], sigma=sigma)
      field.Velocity[:,:,:,1] = scipy.ndimage.gaussian_filter(field.Velocity[:,:,:,1], sigma=sigma)
      field.Velocity[:,:,:,2] = scipy.ndimage.gaussian_filter(field.Velocity[:,:,:,2], sigma=sigma)
      return

    else:
      print("Error: unknown filter for field regularization")
      return



  def setROI(self, ROI):
    profile = np.sum(ROI.Mask, (0,2))
    box = [[0, 0, 0], [0, 0, 0]]
    x = np.where(np.any(ROI.Mask, axis=(1,2)))[0]
    y = np.where(np.any(ROI.Mask, axis=(0,2)))[0]
    z = np.where(np.any(ROI.Mask, axis=(0,1)))[0]

    # box start
    box[0][0] = x[0]
    box[0][1] = y[0]
    box[0][2] = z[0]

    # box stop
    box[1][0] = x[-1]
    box[1][1] = y[-1]
    box[1][2] = z[-1]

    self.ROI_box = box



  def Quick_translation_search(self):

    if(self.Fixed == [] or self.Moving == []): 
      print("Image not defined in registration object")
      return

    print("\nStart quick translation search.\n")

    translation = [0.0, 0.0, 0.0]

    # resample Moving to same resolution as Fixed
    self.Deformed = self.Moving.copy()
    GridSize = np.array(self.Moving.GridSize) * np.array(self.Moving.PixelSpacing) / np.array(self.Fixed.PixelSpacing)
    GridSize = GridSize.astype(np.int)
    self.Deformed.resample_image(GridSize, self.Moving.ImagePositionPatient, self.Fixed.PixelSpacing)

    # search shift in x
    fixed_profile = np.sum(self.Fixed.Image, (0,2))
    moving_profile = np.sum(self.Deformed.Image, (0,2))
    shift = self.Match_profiles(fixed_profile, moving_profile)
    translation[0] = self.Fixed.ImagePositionPatient[0] - self.Moving.ImagePositionPatient[0] + shift * self.Deformed.PixelSpacing[0]
    # search shift in y
    fixed_profile = np.sum(self.Fixed.Image, (1,2))
    moving_profile = np.sum(self.Deformed.Image, (1,2))
    shift = self.Match_profiles(fixed_profile, moving_profile)
    translation[1] = self.Fixed.ImagePositionPatient[1] - self.Moving.ImagePositionPatient[1] + shift * self.Deformed.PixelSpacing[1]

    # search shift in z
    fixed_profile = np.sum(self.Fixed.Image, (0,1))
    moving_profile = np.sum(self.Deformed.Image, (0,1))
    shift = self.Match_profiles(fixed_profile, moving_profile)
    translation[2] = self.Fixed.ImagePositionPatient[2] - self.Moving.ImagePositionPatient[2] + shift * self.Deformed.PixelSpacing[2]

    self.Translate_origin(self.Deformed, translation)

    return translation



  def Match_profiles(self, fixed, moving):
    MSE = []

    for index in range(len(moving)):
      shift = index - round(len(moving)/2)

      # shift profiles
      shifted = np.roll(moving, shift)

      # crop profiles to same size
      if(len(shifted) > len(fixed)):
        vec1 = shifted[:len(fixed)]
        vec2 = fixed
      else:
        vec1 = shifted
        vec2 = fixed[:len(shifted)]

      # compute MSE
      MSE.append(((vec1-vec2)**2).mean())

    return (np.argmin(MSE) - round(len(moving)/2))



  def Translate_and_SSD(self, translation=[0.0, 0.0, 0.0]):

    # crop fixed image to ROI box
    if(self.ROI_box == []):
      fixed = self.Fixed.Image
      Origin = self.Fixed.ImagePositionPatient
      GridSize = self.Fixed.GridSize
    else:
      start = self.ROI_box[0]
      stop = self.ROI_box[1]
      fixed = self.Fixed.Image[start[0]:stop[0], start[1]:stop[1], start[2]:stop[2]]
      Origin = self.Fixed.ImagePositionPatient + np.array([start[1]*self.Fixed.PixelSpacing[0], start[0]*self.Fixed.PixelSpacing[1], start[2]*self.Fixed.PixelSpacing[2]])
      GridSize = list(fixed.shape)

    print("Translation: " + str(translation))

    # deform moving image
    self.Deformed = self.Moving.copy()
    self.Translate_origin(self.Deformed, translation)
    self.Deformed.resample_image(GridSize, Origin, self.Fixed.PixelSpacing)

    # compute metric
    SSD = self.Compute_SSD(fixed, self.Deformed.Image)

    return SSD



  def Compute_SSD(self, fixed, deformed):
    # compute metric
    SSD = np.sum(np.power(fixed - deformed, 2))
    print("SSD: " + str(SSD))

    return SSD



  def Rigid_registration(self, initial_translation=[0.0, 0.0, 0.0]):
    print("\nStart rigid registration.\n")

    opt = scipy.optimize.minimize(self.Translate_and_SSD, initial_translation, method='Powell', options={'xtol': 0.01, 'ftol': 0.0001, 'maxiter': 25, 'maxfev': 75})

    if(self.ROI_box == []):
       translation = opt.x
    else:
      start = self.ROI_box[0]
      stop = self.ROI_box[1]
      translation = opt.x
    
    return translation
    


  def Translate_origin(self, Image, translation):

    Image.ImagePositionPatient[0] += translation[0]
    Image.ImagePositionPatient[1] += translation[1]
    Image.ImagePositionPatient[2] += translation[2]

    Image.VoxelX = Image.ImagePositionPatient[0] + np.arange(Image.GridSize[0])*Image.PixelSpacing[0]
    Image.VoxelY = Image.ImagePositionPatient[1] + np.arange(Image.GridSize[1])*Image.PixelSpacing[1]
    Image.VoxelZ = Image.ImagePositionPatient[2] + np.arange(Image.GridSize[2])*Image.PixelSpacing[2]



  def Resample_moving_image(self, KeepFixedShape=True):
    if(self.Fixed == [] or self.Moving == []): 
      print("Image not defined in registration object")
      return

    if(KeepFixedShape == True):
      resampled = self.Moving.copy()
      resampled.resample_image(self.Fixed.GridSize, self.Fixed.ImagePositionPatient, self.Fixed.PixelSpacing)

    else:
      X_min = min(self.Fixed.ImagePositionPatient[0], self.Moving.ImagePositionPatient[0])
      Y_min = min(self.Fixed.ImagePositionPatient[1], self.Moving.ImagePositionPatient[1])
      Z_min = min(self.Fixed.ImagePositionPatient[2], self.Moving.ImagePositionPatient[2])
      
      X_max = max(self.Fixed.VoxelX[-1], self.Moving.VoxelX[-1])
      Y_max = max(self.Fixed.VoxelY[-1], self.Moving.VoxelY[-1])
      Z_max = max(self.Fixed.VoxelZ[-1], self.Moving.VoxelZ[-1])

      Offset = [X_min, Y_min, Z_min]
      GridSize_x = round((X_max-X_min)/self.Fixed.PixelSpacing[0])
      GridSize_y = round((Y_max-Y_min)/self.Fixed.PixelSpacing[1])
      GridSize_z = round((Z_max-Z_min)/self.Fixed.PixelSpacing[2])
      GridSize = [GridSize_x, GridSize_y, GridSize_z]

      resampled = self.Moving.copy()
      resampled.resample_image(GridSize, Offset, self.Fixed.PixelSpacing)

    return resampled



  def Resample_fixed_image(self):

    if(self.Fixed == [] or self.Moving == []): 
      print("Image not defined in registration object")
      return

    X_min = min(self.Fixed.ImagePositionPatient[0], self.Moving.ImagePositionPatient[0])
    Y_min = min(self.Fixed.ImagePositionPatient[1], self.Moving.ImagePositionPatient[1])
    Z_min = min(self.Fixed.ImagePositionPatient[2], self.Moving.ImagePositionPatient[2])
      
    X_max = max(self.Fixed.VoxelX[-1], self.Moving.VoxelX[-1])
    Y_max = max(self.Fixed.VoxelY[-1], self.Moving.VoxelY[-1])
    Z_max = max(self.Fixed.VoxelZ[-1], self.Moving.VoxelZ[-1])

    Offset = [X_min, Y_min, Z_min]
    GridSize_x = round((X_max-X_min)/self.Fixed.PixelSpacing[0])
    GridSize_y = round((Y_max-Y_min)/self.Fixed.PixelSpacing[1])
    GridSize_z = round((Z_max-Z_min)/self.Fixed.PixelSpacing[2])
    GridSize = [GridSize_x, GridSize_y, GridSize_z]

    resampled = self.Fixed.copy()
    resampled.resample_image(GridSize, Offset, self.Fixed.PixelSpacing)

    return resampled



  def Image_difference(self, KeepFixedShape=True):

    if(self.Fixed == [] or self.Moving == []): 
      print("Image not defined in registration object")
      return    

    if(KeepFixedShape == True):
      diff = self.Resample_moving_image(KeepFixedShape=True)
      diff.Image = self.Fixed.Image - diff.Image

    else:
      diff = self.Resample_moving_image(KeepFixedShape=False)
      tmp = self.Resample_fixed_image()
      diff.Image = tmp.Image - diff.Image

    return diff

