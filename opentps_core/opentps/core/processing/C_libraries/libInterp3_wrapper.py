import os
import numpy as np
import ctypes
import scipy.interpolate
import platform
import logging

try:
    import cupy
    import cupyx
    # cupy.cuda.Device(0).use()
except:
    print('cupy not found.')

logger = logging.getLogger(__name__)

def interpolateTrilinear(image, gridSize, interpolatedPoints, fillValue=0, tryGPU=True):

  interpolatedImage = None

  if image.size > 1e5 and tryGPU:
    if interpolatedImage is None:
      try:
        interpolatedImage = cupy.asnumpy(cupyx.scipy.ndimage.map_coordinates(cupy.asarray(image), cupy.asarray(interpolatedPoints.T), order=1, mode='constant', cval=fillValue))
      except:
        logger.info('cupy 3D interpolation not enabled. The C implementation is tried instead')

  if interpolatedImage is None:
    try:
      # import C library
      if(platform.system() == "Linux"): libInterp3 = ctypes.cdll.LoadLibrary(os.path.join(os.path.dirname(__file__),
                                                                                          "libInterp3.so"))
      elif(platform.system() == "Windows"): libInterp3 = ctypes.cdll.LoadLibrary(os.path.join(os.path.dirname(__file__),
                                                                                              "libInterp3.dll"))
      else: print("Error: not compatible with " + platform.system() + " system.")
      float_array = np.ctypeslib.ndpointer(dtype=np.float32)
      int_array = np.ctypeslib.ndpointer(dtype=np.int32)
      libInterp3.Trilinear_Interpolation.argtypes = [float_array, int_array, float_array, ctypes.c_int, ctypes.c_float, float_array]
      libInterp3.Trilinear_Interpolation.restype = ctypes.c_void_p

      # prepare inputs for C library
      Img = np.array(image, dtype=np.float32, order='C')
      Size = np.array(gridSize, dtype=np.int32, order='C')
      Points = np.array(interpolatedPoints, dtype=np.float32, order='C')
      NumPoints = interpolatedPoints.shape[0]
      interpolatedImage = np.zeros(NumPoints, dtype=np.float32, order='C')

      # call C function
      libInterp3.Trilinear_Interpolation(Img, Size, Points, NumPoints, fillValue, interpolatedImage)

    except:
      # print('accelerated 3D interpolation not enabled. The python implementation is used instead')
      logger.info('accelerated 3D interpolation not enabled. The python implementation is used instead')
      # print('accelerated 3D interpolation not enabled. The python implementation is used instead')


  if interpolatedImage is None:
    # voxel coordinates of the original image
    x = np.arange(gridSize[0])
    y = np.arange(gridSize[1])
    z = np.arange(gridSize[2])

    interpolatedImage = scipy.interpolate.interpn((x, y, z), image, interpolatedPoints, method='linear', fill_value=fillValue, bounds_error=False)

  return interpolatedImage
