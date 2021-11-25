
import numpy as np
import os
import scipy.optimize
import scipy.ndimage
import scipy.signal

import multiprocessing as mp
from functools import partial

from Core.Data.deformationField import *

def morphonsConv(im, k):
  return scipy.signal.fftconvolve(im, k, mode='same')

def morphonsComplexConvS(im, k):
  return scipy.signal.fftconvolve(im, np.real(k), mode='same') + scipy.signal.fftconvolve(im, np.imag(k), mode='same') * 1j

def morphonsComplexConvD(im, k):
  return scipy.signal.fftconvolve(im, np.real(k), mode='same') - scipy.signal.fftconvolve(im, np.imag(k), mode='same') * 1j

class Registration:

  def __init__(self, Fixed, Moving):
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
    field.Init_Field_Zeros(self.Fixed.Image.shape, Offset=self.Fixed.ImagePositionPatient, PixelSpacing=self.Fixed.PixelSpacing)

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
      deformed = field.deform_image(self.Moving)

    self.Deformed = self.Moving.copy()
    self.Deformed.Image = deformed

    return field



  def Registration_morphons(self, base_resolution=2.5, nb_processes=-1):

    if nb_processes < 0:
      nb_processes = min(mp.cpu_count(), 6)

    if nb_processes > 1:
      pool = mp.Pool(nb_processes)

    eps = np.finfo("float64").eps
    eps32 = np.finfo("float32").eps
    scales = base_resolution*np.asarray([11.3137, 8.0, 5.6569, 4.0, 2.8284, 2.0, 1.4142, 1.0])
    iterations = [10, 10, 10, 10, 10, 10, 5, 2]
    q_directions = [[0, 0.5257, 0.8507],[0, -0.5257, 0.8507],[0.5257, 0.8507, 0],[-0.5257, 0.8507, 0],[0.8507, 0, 0.5257],[0.8507, 0, -0.5257]]

    morphons_path = os.path.abspath("./Process/Morphons_kernels")
    k = []
    k.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel1_real.bin"), dtype="float64")) + np.float32(np.fromfile(os.path.join(morphons_path, "kernel1_imag.bin"), dtype="float64"))*1j, (9,9,9)))
    k.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel2_real.bin"), dtype="float64")) + np.float32(np.fromfile(os.path.join(morphons_path, "kernel2_imag.bin"), dtype="float64"))*1j, (9,9,9)))
    k.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel3_real.bin"), dtype="float64")) + np.float32(np.fromfile(os.path.join(morphons_path, "kernel3_imag.bin"), dtype="float64"))*1j, (9,9,9)))
    k.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel4_real.bin"), dtype="float64")) + np.float32(np.fromfile(os.path.join(morphons_path, "kernel4_imag.bin"), dtype="float64"))*1j, (9,9,9)))
    k.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel5_real.bin"), dtype="float64")) + np.float32(np.fromfile(os.path.join(morphons_path, "kernel5_imag.bin"), dtype="float64"))*1j, (9,9,9)))
    k.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel6_real.bin"), dtype="float64")) + np.float32(np.fromfile(os.path.join(morphons_path, "kernel6_imag.bin"), dtype="float64"))*1j, (9,9,9)))

    k_new = []
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel1_real.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel2_real.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel3_real.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel4_real.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel5_real.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel6_real.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel1_imag.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel2_imag.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel3_imag.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel4_imag.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel5_imag.bin"), dtype="float64")), (9,9,9)))
    k_new.append(np.reshape(np.float32(np.fromfile(os.path.join(morphons_path, "kernel6_imag.bin"), dtype="float64")), (9,9,9)))


    field = DeformationField()

    for s in range(len(scales)):

      # Compute grid for new scale
      new_grid_size = [round(self.Fixed.PixelSpacing[1]/scales[s]*self.Fixed.GridSize[0]),
                       round(self.Fixed.PixelSpacing[0]/scales[s]*self.Fixed.GridSize[1]),
                       round(self.Fixed.PixelSpacing[2]/scales[s]*self.Fixed.GridSize[2])]
      new_voxel_spacing = [self.Fixed.PixelSpacing[0]*(self.Fixed.GridSize[1]-1)/(new_grid_size[1]-1),
                           self.Fixed.PixelSpacing[1]*(self.Fixed.GridSize[0]-1)/(new_grid_size[0]-1),
                           self.Fixed.PixelSpacing[2]*(self.Fixed.GridSize[2]-1)/(new_grid_size[2]-1)]

      print('Morphons scale:', s + 1, '/', len(scales), ' (',
            round(new_voxel_spacing[0] * 1e2) / 1e2, 'x',
            round(new_voxel_spacing[1] * 1e2) / 1e2, 'x',
            round(new_voxel_spacing[2] * 1e2) / 1e2, 'mm3)')

      # Resample fixed and moving images and field according to the considered scale (voxel spacing)
      fixed_resampled = self.Fixed.copy()
      fixed_resampled.resample_image(new_grid_size, self.Fixed.ImagePositionPatient, new_voxel_spacing)
      moving_resampled = self.Moving.copy()
      moving_resampled.resample_image(fixed_resampled.GridSize, fixed_resampled.ImagePositionPatient, fixed_resampled.PixelSpacing)

      if s != 0:
        field.resample_to_CT_grid(fixed_resampled, 'Velocity')
        certainty.resample_image(fixed_resampled.GridSize, fixed_resampled.ImagePositionPatient, fixed_resampled.PixelSpacing, fill_value=0)
      else:
        field.Init_Field_Zeros(fixed_resampled.Image.shape, Offset=fixed_resampled.ImagePositionPatient, PixelSpacing=fixed_resampled.PixelSpacing)
        certainty = fixed_resampled.copy()
        certainty.Image = np.zeros_like(certainty.Image)

      # Compute phase on fixed image
      if(nb_processes>1):
        pconv = partial(morphonsComplexConvS, fixed_resampled.Image)
        q_fixed = pool.map(pconv, k)
      else:
        q_fixed = []
        for n in range(6):
          q_fixed.append(scipy.signal.fftconvolve(fixed_resampled.Image, np.real(k[n]), mode='same') + scipy.signal.fftconvolve(fixed_resampled.Image, np.imag(k[n]), mode='same') * 1j)

      for i in range(iterations[s]):

        # Deform moving image
        deformed = moving_resampled.copy()
        if s != 0 or i != 0:
          deformed.Image = field.deform_image(deformed, fill_value='closest')

        # Compute phase difference
        a11 = np.zeros_like(q_fixed[0], dtype="float64")
        a12 = np.zeros_like(q_fixed[0], dtype="float64")
        a13 = np.zeros_like(q_fixed[0], dtype="float64")
        a22 = np.zeros_like(q_fixed[0], dtype="float64")
        a23 = np.zeros_like(q_fixed[0], dtype="float64")
        a33 = np.zeros_like(q_fixed[0], dtype="float64")
        b1 = np.zeros_like(q_fixed[0], dtype="float64")
        b2 = np.zeros_like(q_fixed[0], dtype="float64")
        b3 = np.zeros_like(q_fixed[0], dtype="float64")

        if(nb_processes>1):
          pconv = partial(morphonsComplexConvD, deformed.Image)
          q_deformed = pool.map(pconv, k)
        else:
          q_deformed = []
          for n in range(6):
            q_deformed.append(
              scipy.signal.fftconvolve(deformed.Image, np.real(k[n]), mode='same') - scipy.signal.fftconvolve(deformed.Image, np.imag(k[n]), mode='same') * 1j)

        for n in range(6):

          qq = np.multiply(q_fixed[n], q_deformed[n])

          vk = np.divide(np.imag(qq), np.absolute(qq) + eps32)
          ck2 = np.multiply(np.sqrt(np.absolute(qq)), np.power(np.cos(np.divide(vk, 2)), 4))
          vk = np.multiply(vk, ck2)

          # Add contributions to the equation system
          b1 += q_directions[n][0] * vk
          a11 += q_directions[n][0] * q_directions[n][0] * ck2
          a12 += q_directions[n][0] * q_directions[n][1] * ck2
          a13 += q_directions[n][0] * q_directions[n][2] * ck2
          b2 += q_directions[n][1] * vk
          a22 += q_directions[n][1] * q_directions[n][1] * ck2
          a23 += q_directions[n][2] * q_directions[n][1] * ck2
          b3 += q_directions[n][2] * vk
          a33 += q_directions[n][2] * q_directions[n][2] * ck2

        field_update = np.zeros_like(field.Velocity)
        field_update[:, :, :, 0] = (a22 * a33 - np.power(a23, 2)) * b1 + (a13 * a23 - a12 * a33) * b2 + (
                  a12 * a23 - a13 * a22) * b3
        field_update[:, :, :, 1] = (a13 * a23 - a12 * a33) * b1 + (a11 * a33 - np.power(a13, 2)) * b2 + (
                  a12 * a13 - a11 * a23) * b3
        field_update[:, :, :, 2] = (a12 * a23 - a13 * a22) * b1 + (a12 * a13 - a11 * a23) * b2 + (
                  a11 * a22 - np.power(a12, 2)) * b3
        certainty_update = a11 + a22 + a33

        # Corrections
        det = a11 * a22 * a33 + 2 * a12 * a13 * a23 - np.power(a13,2) * a22 - a11 * np.power(a23,2) - np.power(a12,2) * a33

        z = (det == 0)
        det[z] = 1
        field_update[z, 0] = 0
        field_update[z, 1] = 0
        field_update[z, 2] = 0
        certainty_update[z] = 0
        field_update[:, :, :, 0] = -np.divide(field_update[:, :, :, 0], det)
        field_update[:, :, :, 1] = -np.divide(field_update[:, :, :, 1], det)
        field_update[:, :, :, 2] = -np.divide(field_update[:, :, :, 2], det)

        # Accumulate field and certainty
        field.Velocity[:, :, :, 0] += np.multiply(field_update[:, :, :, 0], np.divide(certainty_update, certainty.Image + certainty_update+eps))
        field.Velocity[:, :, :, 1] += np.multiply(field_update[:, :, :, 1], np.divide(certainty_update, certainty.Image + certainty_update+eps))
        field.Velocity[:, :, :, 2] += np.multiply(field_update[:, :, :, 2], np.divide(certainty_update, certainty.Image + certainty_update+eps))
        certainty.Image = np.divide(np.power(certainty.Image,2) + np.power(certainty_update,2), certainty.Image + certainty_update+eps)

        # Regularize velocity field and certainty
        self.Regularization(field, filter="NormalizedGaussian", sigma=1.25, cert=certainty.Image)
        certainty.Image = self.normGaussConv(certainty.Image, certainty.Image, 1.25)

    self.Deformed = self.Moving.copy()
    self.Deformed.Image = field.deform_image(self.Deformed, fill_value='closest')

    return field



  def Regularization(self, field, filter="Gaussian", sigma=1.0, cert=None):

    if(filter == "Gaussian"):
      field.Velocity[:,:,:,0] = scipy.ndimage.gaussian_filter(field.Velocity[:,:,:,0], sigma=sigma)
      field.Velocity[:,:,:,1] = scipy.ndimage.gaussian_filter(field.Velocity[:,:,:,1], sigma=sigma)
      field.Velocity[:,:,:,2] = scipy.ndimage.gaussian_filter(field.Velocity[:,:,:,2], sigma=sigma)
      return

    if (filter == "NormalizedGaussian"):
      if cert is None:
        cert = np.ones_like(field.Velocity[:, :, :, 0])
      field.Velocity[:, :, :, 0] = self.normGaussConv(field.Velocity[:, :, :, 0], cert, sigma)
      field.Velocity[:, :, :, 1] = self.normGaussConv(field.Velocity[:, :, :, 1], cert, sigma)
      field.Velocity[:, :, :, 2] = self.normGaussConv(field.Velocity[:, :, :, 2], cert, sigma)
      return

    else:
      print("Error: unknown filter for field regularization")
      return



  def normGaussConv(self, data, cert, sigma):

    data = scipy.ndimage.gaussian_filter(np.multiply(data, cert), sigma=sigma)
    cert = scipy.ndimage.gaussian_filter(cert, sigma=sigma)
    z = (cert==0)
    data[z] = 0.0
    cert[z] = 1.0
    data = np.divide(data, cert)
    return data



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
    # print("SSD: " + str(SSD))

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
