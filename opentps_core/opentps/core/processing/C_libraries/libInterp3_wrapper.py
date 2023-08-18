import os
import numpy as np
import ctypes
import scipy.interpolate
import platform
import logging

logger = logging.getLogger(__name__)
#logger.setLevel(logging.WARNING)

try:
    import cupy
    import cupyx
    # cupy.cuda.Device(0).use()
except:
    logger.warning('cupy not found.')


def interpolateTrilinear(image, gridSize, interpolatedPoints, fillValue=0, tryGPU=True):
  """
    Interpolate a 3D image using trilinear interpolation.

    Parameters
    ----------
    image : numpy.ndarray
        3D image to be interpolated.
    gridSize : tuple
        Size of the 3D image.
    interpolatedPoints : numpy.ndarray
        3D coordinates of the points to be interpolated.
    fillValue : float, optional
        Value to be used for points outside the image. The default is 0.
    tryGPU : bool, optional
        Try to use GPU for interpolation. The default is True.

    Returns
    -------
    interpolatedImage : numpy.ndarray
        Interpolated image.
  """

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
      elif (platform.system() == "Darwin"): libInterp3 = ctypes.cdll.LoadLibrary(os.path.join(os.path.dirname(__file__),
                                                                                              "libInterp3MAC.so"))
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
