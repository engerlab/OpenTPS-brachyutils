from typing import Sequence, Optional

import numpy as np
import time
from Core.Processing.ImageProcessing.sitkImageProcessing import *
from Core.Processing.ImageProcessing import resampler3D
from Core.Data.Images.image3D import Image3D
try:
    import SimpleITK as sitk
except:
    print('No module SimpleITK found')

if __name__ == "__main__":
    data = np.random.randint(0, high=500, size=(216, 216, 216))

    image = Image3D(np.array(data), origin=(0, 0, 0), spacing=(1, 1, 1))
    imageITK = Image3D(np.array(data), origin=(0, 0, 0), spacing=(1, 1, 1))


    start = time.time()
    resize(imageITK, np.array([0.5, 0.5, 0.5]), newOrigin=imageITK.origin, newShape=imageITK.gridSize*2, fillValue=0.)
    end = time.time()
    print('Simple ITK from shape ' + str(image.gridSize) + ' to shape ' + str(imageITK.gridSize) + ' in '+ str(end - start) + ' s')


    start = time.time()
    imageArrayCupy = resampler3D.resample(image.imageArray, image.origin, image.spacing, image.gridSize,
                                          imageITK.origin, imageITK.spacing, imageITK.gridSize,
                                          fillValue=0, outputType=None, tryGPU=True)
    end = time.time()
    print('Cupy from shape ' + str(image.gridSize) + ' to shape ' + str(imageArrayCupy.shape) + ' in ' + str(end - start) + ' s')

    start = time.time()
    imageArrayCupy = resampler3D.resample(image.imageArray, image.origin, image.spacing, image.gridSize,
                                          imageITK.origin, imageITK.spacing, imageITK.gridSize,
                                          fillValue=0, outputType=None, tryGPU=True)
    end = time.time()
    print('Cupy from shape ' + str(image.gridSize) + ' to shape ' + str(imageArrayCupy.shape) + ' in ' + str(
        end - start) + ' s')

    start = time.time()
    imageArrayCupy = resampler3D.resample(image.imageArray, image.origin, image.spacing, image.gridSize,
                                          imageITK.origin, imageITK.spacing, imageITK.gridSize,
                                          fillValue=0, outputType=None, tryGPU=True)
    end = time.time()
    print('Cupy from shape ' + str(image.gridSize) + ' to shape ' + str(imageArrayCupy.shape) + ' in ' + str(
        end - start) + ' s')


    start = time.time()
    imageArrayKevin = resampler3D.resample(image.imageArray, image.origin, image.spacing, image.gridSize,
                                          imageITK.origin, imageITK.spacing, imageITK.gridSize,
                                          fillValue=0, outputType=None, tryGPU=False)
    end = time.time()
    print('Kevin from shape ' + str(image.gridSize) + ' to shape ' + str(imageArrayCupy.shape) + ' in ' + str(
        end - start) + ' s')