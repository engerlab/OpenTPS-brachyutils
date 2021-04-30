import numpy as np
import ctypes
import scipy.interpolate
import platform

def Trilinear_Interpolation(Image, GridSize, InterpolatedPoints, fill_value=0):
  try:
    # import C library
    if(platform.system() == "Linux"): libInterp3 = ctypes.cdll.LoadLibrary("Process/C_libraries/libInterp3.so")
    elif(platform.system() == "Windows"): libInterp3 = ctypes.cdll.LoadLibrary("Process/C_libraries/libInterp3.dll")
    else: print("Error: not compatible with " + platform.system() + " system.")
    float_array = np.ctypeslib.ndpointer(dtype=np.float32)
    int_array = np.ctypeslib.ndpointer(dtype=np.int32)
    libInterp3.Trilinear_Interpolation.argtypes = [float_array, int_array, float_array, ctypes.c_int, ctypes.c_float, float_array]
    libInterp3.Trilinear_Interpolation.restype  = ctypes.c_void_p

    # prepare inputs for C library
    Img = np.array(Image, dtype=np.float32, order='C')
    Size = np.array(GridSize, dtype=np.int32, order='C')
    Points = np.array(InterpolatedPoints, dtype=np.float32, order='C')
    NumPoints = InterpolatedPoints.shape[0]
    Intepolated_img = np.zeros(NumPoints, dtype=np.float32, order='C')

    # call C function
    libInterp3.Trilinear_Interpolation(Img, Size, Points, NumPoints, fill_value, Intepolated_img)

  except:
    print('Warning: accelerated 3D interpolation not enabled. The python implementation is used instead')
    # voxel coordinates of the original image
    x = np.arange(GridSize[0])
    y = np.arange(GridSize[1])
    z = np.arange(GridSize[2])

    Intepolated_img = scipy.interpolate.interpn((x,y,z), Image, InterpolatedPoints, method='linear', fill_value=fill_value, bounds_error=False)
    # f_interp = scipy.interpolate.RegularGridInterpolator((x,y,z), Image, method='linear', fill_value=fill_value, bounds_error=False)
    # self.Image = f_interp(InterpolatedPoints)


  return Intepolated_img