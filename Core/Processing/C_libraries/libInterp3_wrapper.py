import numpy as np
import ctypes
import scipy.interpolate
import platform

def interpolateTrilinear(image, gridSize, interpolatedPoints, fillValue=0):
  try:
    # import C library
    if(platform.system() == "Linux"): libInterp3 = ctypes.cdll.LoadLibrary("Core/Processing/C_libraries/libInterp3.so")
    elif(platform.system() == "Windows"): libInterp3 = ctypes.cdll.LoadLibrary("Core/Processing/C_libraries/libInterp3.dll")
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
    print('Warning: accelerated 3D interpolation not enabled. The python implementation is used instead')
    # voxel coordinates of the original image
    x = np.arange(gridSize[0])
    y = np.arange(gridSize[1])
    z = np.arange(gridSize[2])

    interpolatedImage = scipy.interpolate.interpn((x,y,z), image, interpolatedPoints, method='linear', fill_value=fillValue, bounds_error=False)
    # f_interp = scipy.interpolate.RegularGridInterpolator((x,y,z), image, method='linear', fill_value=fillValue, bounds_error=False)
    # self.image = f_interp(interpolatedPoints)

  return interpolatedImage
