import os
import sys
import numpy as np

def export_CT_for_MCsquare(CT, file_path):
  
  if CT.GridSize[0] != CT.GridSize[1]:
    print("WARNING: different number of voxels in X and Y directions may not be fully supported")

  # Convert data for compatibility with MCsquare
  # These transformations may be modified in a future version
  image = np.flip(CT.Image, 0)
  image = np.flip(image, 1)

  # Parse file path
  DestFolder, DestFile = os.path.split(file_path)
  FileName, FileExtension = os.path.splitext(DestFile)

  if FileExtension == ".mhd" or FileExtension == ".MHD":
    MHD_File = DestFile
    RAW_File = FileName + ".raw"
  else:
    MHD_File = DestFile + ".mhd"
    RAW_File = DestFile + ".raw"
    
      
  # Write header file (MHD)
  print("Write MHD CT: " + os.path.join(DestFolder, MHD_File))
  fid = open(os.path.join(DestFolder, MHD_File),"w") 
  fid.write("ObjectType = Image\n") 
  fid.write("NDims = 3\n") 
  fid.write("DimSize = %d %d %d\n" % tuple(CT.GridSize))
  fid.write("ElementSpacing = %f %f %f\n" % tuple(CT.PixelSpacing))
  fid.write("Offset = %f %f %f\n" % tuple(CT.ImagePositionPatient))
  fid.write("ElementType = MET_FLOAT\n") 
  fid.write("ElementByteOrderMSB = False\n") 
  fid.write("ElementDataFile = %s\n" % RAW_File)
  fid.close()
  
  # convert data type
  if image.dtype != "float32":
    image = image.astype("float32")
    
  if image.dtype.byteorder == '>':
    image.byteswap() 
  elif image.dtype.byteorder == '=' and sys.byteorder != "little":
    image.byteswap()
  
  # Write binary file (RAW)
  fid = open(os.path.join(DestFolder, RAW_File),"w") 
  image.transpose(1,0,2).reshape(CT.NumVoxels, order='F').tofile(fid)
  fid.close()
  
  
  
