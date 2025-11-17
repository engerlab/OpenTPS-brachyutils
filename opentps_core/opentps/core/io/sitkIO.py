import os, sys
import numpy as np
import logging

from opentps.core.data.images._image3D import Image3D
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.images._vectorField3D import VectorField3D
import SimpleITK as sitk

def CreateDir(dir):
  if not os.path.isdir(dir):
    os.makedirs(dir)

def SaveImage(itk_img, path, type = None):
  if type:
    itk_img = sitk.Cast(itk_img, type)
  CreateDir(os.path.dirname(path))
  ifw = sitk.ImageFileWriter()
  ifw.SetFileName(path)
  ifw.SetUseCompression(True)
  ifw.Execute(itk_img)

def convertImageToSitk(image: Image3D, mask = False):
    img_array = image._imageArray * 1.0 ### Convert bool to float
    if mask:
      img_array = img_array.astype(np.uint8)
    img_sitk = sitk.GetImageFromArray(np.transpose(img_array))
    img_sitk.SetOrigin(np.array(image.origin, float))
    img_sitk.SetSpacing(np.array(image.spacing, float))
    return img_sitk

def exportImageSitk(outputPath, image: Image3D, mask = False):
    img_sitk = convertImageToSitk(image, mask)
    SaveImage(img_sitk, outputPath)

def readImage(path, ROI = False):
   fileName = os.path.basename(path)
   fileName = '.'.join(os.path.basename(path).split('.')[:-2])
   image = sitk.ReadImage(path)
   imageArray = np.transpose(sitk.GetArrayFromImage(image))
   if ROI:
      return ROIMask(imageArray=imageArray, name=fileName, origin=image.GetOrigin(), spacing=image.GetSpacing())
   else:
      return Image3D(imageArray=imageArray, name=fileName, origin=image.GetOrigin(), spacing=image.GetSpacing())


def getOriginTransformed(origing, translationPath):
  transform = sitk.ReadTransform(translationPath)
  shift = np.array(transform.GetParameters()[3:])
  return (origing - shift)