import os
import numpy as np
import math
import time

import warnings
warnings.filterwarnings('ignore',category=FutureWarning)

try:
  import keras
  use_keras = 1
except:
  use_keras = 0

from Process.DeepLearning_denoising.simpleNet_3d import *
from Process.DeepLearning_denoising.dilatedUnet_3d import *

def Denoise_MC_dose(NoisyImage, model='sNet_7'):

  if use_keras == 0:
    print('Error: keras/tensorflow not installed.')
    return np.zeros(NoisyImage.shape)

  if(model == 'sNet_7'): return sNet_7_model(NoisyImage)
  elif(model == 'sNet_24'): return sNet_24_model(NoisyImage)
  elif(model == 'dUNet_7'): return dUNet_7_model(NoisyImage)
  elif(model == 'dUNet_24'): return dUNet_24_model(NoisyImage)
  


def sNet_24_model(NoisyImage):
  if use_keras == 0:
    print('Error: keras/tensorflow not installed.')
    return np.zeros(NoisyImage.shape)

  # model parameters
  fixedDepth = 24
  discarded_slices = 5
  filters = 24
  height = 512
  width = 512
  channels = 1
  Module_folder = os.path.dirname(os.path.realpath(__file__))
  weightFile = os.path.join(Module_folder, "models", "sNet_24_24Filters_B1.h5")
  
  time_start = time.time()
  
  # load model
  model = simpleNet(height=height, width=width, channels=channels, classes=fixedDepth, features=filters, depth=3, padding='same')
  model.load_weights(weightFile)
  #model.summary()
  model.compile(optimizer=keras.optimizers.Adam(1e-4), loss=keras.losses.mean_squared_error, metrics=[keras.losses.mean_absolute_error])
  
  # padding needed if GridSize < 512x512
  bottomPadding = (height - NoisyImage.shape[0]) // 2
  topPadding = height - NoisyImage.shape[0] - bottomPadding
  leftPadding = (width - NoisyImage.shape[1]) // 2
  rightPadding = width - NoisyImage.shape[1] - leftPadding
  
  DenoisedImage = np.zeros(NoisyImage.shape)
  zeroArray = np.zeros((NoisyImage.shape[0], NoisyImage.shape[1], discarded_slices)) 
  Input = np.concatenate((zeroArray, NoisyImage), axis=2)
  zeroArray = np.zeros((NoisyImage.shape[0], NoisyImage.shape[1], fixedDepth+discarded_slices)) 
  Input = np.concatenate((Input, zeroArray), axis=2)
  
  NumSlices = (fixedDepth-2*discarded_slices)
  NumSubVolumes = math.ceil(NoisyImage.shape[2] / NumSlices)
  for i in range(NumSubVolumes):
    print('denoise subvolume ' + str(i+1) + '/' + str(NumSubVolumes))
    SubVolume = Input[:,:,i*NumSlices:(i+1)*NumSlices+2*discarded_slices]
    SubVolume = SubVolume.transpose(2,0,1)
    SubVolume = np.pad(SubVolume, ((0,0), (bottomPadding,topPadding), (leftPadding,rightPadding)))
    SubVolume = np.expand_dims(SubVolume, axis=-1)
    SubVolume = np.expand_dims(SubVolume, axis=0)
    SubVolume = model.predict(SubVolume)
    if(i == NumSubVolumes-1):
      RemainingSlices = NoisyImage.shape[2] - (i+1)*NumSlices - discarded_slices
      DenoisedImage[:, :, i*NumSlices:] = SubVolume[0, discarded_slices:RemainingSlices, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0].transpose(1,2,0)
    else:
      DenoisedImage[:, :, i*NumSlices:(i+1)*NumSlices] = SubVolume[0, discarded_slices:-discarded_slices, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0].transpose(1,2,0)
      
  DenoisedImage[DenoisedImage < 0.0] = 0.0
  
  print('sNet_24 denoising in ' + str(time.time()-time_start) + ' sec')
  
  return DenoisedImage
  


def dUNet_24_model(NoisyImage):
  if use_keras == 0:
    print('Error: keras/tensorflow not installed.')
    return np.zeros(NoisyImage.shape)

  # model parameters
  fixedDepth = 24
  discarded_slices = 5
  filters = 24
  height = 512
  width = 512
  channels = 1
  Module_folder = os.path.dirname(os.path.realpath(__file__))
  weightFile = os.path.join(Module_folder, "models", "dUNet_24_24Filters_B1.h5")
  
  time_start = time.time()
  
  # load model
  model = dilated_unet(height=height, width=width, channels=channels, classes=fixedDepth, features=filters, depth=3, padding='same', residual=False, strides=(2,2,2))
  model.load_weights(weightFile)
  #model.summary()
  model.compile(optimizer=keras.optimizers.Adam(1e-4), loss=keras.losses.mean_squared_error, metrics=[keras.losses.mean_absolute_error])
  
  # padding needed if GridSize < 512x512
  bottomPadding = (height - NoisyImage.shape[0]) // 2
  topPadding = height - NoisyImage.shape[0] - bottomPadding
  leftPadding = (width - NoisyImage.shape[1]) // 2
  rightPadding = width - NoisyImage.shape[1] - leftPadding
  
  DenoisedImage = np.zeros(NoisyImage.shape)
  zeroArray = np.zeros((NoisyImage.shape[0], NoisyImage.shape[1], discarded_slices)) 
  Input = np.concatenate((zeroArray, NoisyImage), axis=2)
  zeroArray = np.zeros((NoisyImage.shape[0], NoisyImage.shape[1], fixedDepth+discarded_slices)) 
  Input = np.concatenate((Input, zeroArray), axis=2)
  
  NumSlices = (fixedDepth-2*discarded_slices)
  NumSubVolumes = math.ceil(NoisyImage.shape[2] / NumSlices)
  for i in range(NumSubVolumes):
    print('denoise subvolume ' + str(i+1) + '/' + str(NumSubVolumes))
    SubVolume = Input[:,:,i*NumSlices:(i+1)*NumSlices+2*discarded_slices]
    SubVolume = SubVolume.transpose(2,0,1)
    SubVolume = np.pad(SubVolume, ((0,0), (bottomPadding,topPadding), (leftPadding,rightPadding)))
    SubVolume = np.expand_dims(SubVolume, axis=-1)
    SubVolume = np.expand_dims(SubVolume, axis=0)
    SubVolume = model.predict(SubVolume)
    if(i == NumSubVolumes-1):
      RemainingSlices = NoisyImage.shape[2] - (i+1)*NumSlices - discarded_slices
      DenoisedImage[:, :, i*NumSlices:] = SubVolume[0, discarded_slices:RemainingSlices, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0].transpose(1,2,0)
    else:
      DenoisedImage[:, :, i*NumSlices:(i+1)*NumSlices] = SubVolume[0, discarded_slices:-discarded_slices, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0].transpose(1,2,0)
      
  DenoisedImage[DenoisedImage < 0.0] = 0.0
  
  print('dUNet_24 denoising in ' + str(time.time()-time_start) + ' sec')
  
  return DenoisedImage
  
  

def sNet_7_model(NoisyImage):
  if use_keras == 0:
    print('Error: keras/tensorflow not installed.')
    return np.zeros(NoisyImage.shape)

  # model parameters
  context = 7
  filters = 24
  height = 512
  width = 512
  channels = 1
  Module_folder = os.path.dirname(os.path.realpath(__file__))
  weightFile = os.path.join(Module_folder, "models", "sNet_7_24Filters_B2.h5")
  
  time_start = time.time()
  
  # load model
  model = simpleNet(height=height, width=width, channels=channels, classes=context, features=filters, depth=3, padding='same')  
  model.load_weights(weightFile)
  #model.summary()
  model.compile(optimizer=keras.optimizers.Adam(1e-4), loss=keras.losses.mean_squared_error, metrics=[keras.losses.mean_absolute_error])
  
  # padding needed if GridSize < 512x512
  bottomPadding = (height - NoisyImage.shape[0]) // 2
  topPadding = height - NoisyImage.shape[0] - bottomPadding
  leftPadding = (width - NoisyImage.shape[1]) // 2
  rightPadding = width - NoisyImage.shape[1] - leftPadding
  
  # denoise image slice by slice
  DenoisedImage = np.zeros(NoisyImage.shape)
  for i in range(NoisyImage.shape[2] - context + 1):
    print('denoise subvolume ' + str(i+1) + '/' + str(NoisyImage.shape[2] - context + 1))
    SubVolume = NoisyImage[:,:,i:i+context]
    SubVolume = SubVolume.transpose(2,0,1)
    SubVolume = np.pad(SubVolume, ((0,0), (bottomPadding,topPadding), (leftPadding,rightPadding)))
    SubVolume = np.expand_dims(SubVolume, axis=-1)
    SubVolume = np.expand_dims(SubVolume, axis=0)
    SubVolume = model.predict(SubVolume)
    if(i == 0):
      DenoisedImage[:, :, :context//2+1] = SubVolume[0, :context//2+1, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0].transpose(1,2,0)
    elif(i == NoisyImage.shape[2] - context):
      DenoisedImage[:, :, i+context//2:] = SubVolume[0, context//2:, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0].transpose(1,2,0)
    else:
      DenoisedImage[:, :, i+context//2] = SubVolume[0, context//2, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0]
  
  DenoisedImage[DenoisedImage < 0.0] = 0.0

  print('sNet_7 denoising in ' + str(time.time()-time_start) + ' sec')
  
  return DenoisedImage
  
  

def dUNet_7_model(NoisyImage):
  if use_keras == 0:
    print('Error: keras/tensorflow not installed.')
    return np.zeros(NoisyImage.shape)
    
  # model parameters
  context = 7
  filters = 24
  height = 512
  width = 512
  channels = 1
  Module_folder = os.path.dirname(os.path.realpath(__file__))
  weightFile = os.path.join(Module_folder, "models", "dUNet_7_24Filters_B2.h5")
  
  time_start = time.time()
  
  # load model
  model = dilated_unet(height=height, width=width, channels=channels, classes=context, features=filters, depth=3, padding='same', residual=False, strides=(1,2,2)) 
  model.load_weights(weightFile)
  #model.summary()
  model.compile(optimizer=keras.optimizers.Adam(1e-4), loss=keras.losses.mean_squared_error, metrics=[keras.losses.mean_absolute_error])
  
  # padding needed if GridSize < 512x512
  bottomPadding = (height - NoisyImage.shape[0]) // 2
  topPadding = height - NoisyImage.shape[0] - bottomPadding
  leftPadding = (width - NoisyImage.shape[1]) // 2
  rightPadding = width - NoisyImage.shape[1] - leftPadding
  
  # denoise image slice by slice
  DenoisedImage = np.zeros(NoisyImage.shape)
  for i in range(NoisyImage.shape[2] - context + 1):
    print('denoise subvolume ' + str(i+1) + '/' + str(NoisyImage.shape[2] - context + 1))
    SubVolume = NoisyImage[:,:,i:i+context]
    SubVolume = SubVolume.transpose(2,0,1)
    SubVolume = np.pad(SubVolume, ((0,0), (bottomPadding,topPadding), (leftPadding,rightPadding)))
    SubVolume = np.expand_dims(SubVolume, axis=-1)
    SubVolume = np.expand_dims(SubVolume, axis=0)
    SubVolume = model.predict(SubVolume)
    if(i == 0):
      DenoisedImage[:, :, :context//2+1] = SubVolume[0, :context//2+1, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0].transpose(1,2,0)
    elif(i == NoisyImage.shape[2] - context):
      DenoisedImage[:, :, i+context//2:] = SubVolume[0, context//2:, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0].transpose(1,2,0)
    else:
      DenoisedImage[:, :, i+context//2] = SubVolume[0, context//2, bottomPadding:bottomPadding+NoisyImage.shape[0], leftPadding:leftPadding+NoisyImage.shape[1], 0]
  
  DenoisedImage[DenoisedImage < 0.0] = 0.0

  print('dUNet_7 denoising in ' + str(time.time()-time_start) + ' sec')
  
  return DenoisedImage
