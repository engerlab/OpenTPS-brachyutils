import os
import sys
import numpy as np

class MHD_image:

  def __init__(self):
    self.mhd_file_path = ""
    self.NDims = 3
    self.ElementNumberOfChannels = 1
    self.ElementType = "MET_FLOAT"
    self.ElementByteOrderMSB = 0
    self.ElementDataFile = ""
    self.ImagePositionPatient = [0.0, 0.0, 0.0]
    self.PixelSpacing = [1.0, 1.0, 1.0]
    self.GridSize = [0, 0, 0]
    self.NumVoxels = 0
    self.Image = np.array([])
    
    
  def import_MHD_header(self, file_path):
    self.mhd_file_path = file_path
    
    with open(self.mhd_file_path, 'r') as fid:
      for line in fid:
    
        # remove comments
        if line[0] == '#': continue
        line = line.split('#')[0]
      
        # clean the string and extract key & value
        line = line.replace('\r', '').replace('\n', '').replace('\t', ' ')
        line = line.split('=')
        key = line[0].replace(' ', '')
        value = line[1].split(' ')
        value = list(filter(len, value))
      
        if "NDims" in key:
          self.NDims = int(value[0])
        
        elif "ElementNumberOfChannels" in key:
          self.ElementNumberOfChannels = int(value[0])
        
        elif "DimSize" in key:
          self.GridSize = [int(value[0]), int(value[1]), int(value[2])]
          self.NumVoxels = self.GridSize[0] * self.GridSize[1] * self.GridSize[2]
        
        elif "ElementSpacing" in key:
          self.PixelSpacing = [float(value[0]), float(value[1]), float(value[2])]
        
        elif "Offset" in key:
          self.ImagePositionPatient = [float(value[0]), float(value[1]), float(value[2])]
        
        elif "ElementType" in key:
          self.ElementType = value[0]
          if value[0] != "MET_FLOAT" and value[0] != "MET_DOUBLE":
            print("WARNING: unknown ElementType " + value[0])
      
        elif "ElementByteOrderMSB" in key:
          self.ElementByteOrderMSB = bool(value[0])
        
        elif "ElementDataFile" in key:
          if os.path.isabs(value[0]):
            self.ElementDataFile = value[0]
          else:
            DataFolder, DataFile = os.path.split(file_path)
            self.ElementDataFile = os.path.join(DataFolder, value[0])
  
  
  
  def export_MHD_header(self, file_path):
    self.mhd_file_path = file_path
  
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
    fid.write("NDims = %d\n" % self.NDims) 
    fid.write("DimSize = %d %d %d\n" % tuple(self.GridSize))
    fid.write("ElementSpacing = %f %f %f\n" % tuple(self.PixelSpacing))
    fid.write("Offset = %f %f %f\n" % tuple(self.ImagePositionPatient))
    fid.write("ElementType = MET_FLOAT\n") 
    fid.write("ElementByteOrderMSB = False\n") 
    fid.write("ElementDataFile = %s\n" % RAW_File)
    fid.close()
          
          
          
  def import_MHD_data(self):

    if not os.path.isfile(self.ElementDataFile):
      print("ERROR: file " + self.ElementDataFile + " not found!")
      return None
    
    if self.ElementType == "MET_DOUBLE":
      self.Image = np.fromfile(self.ElementDataFile, dtype=np.float)
    else:
      self.Image = np.fromfile(self.ElementDataFile, dtype=np.float32)
      
    self.Image = self.Image.reshape(self.GridSize, order='F').transpose(1,0,2)
    
  
    
  def export_MHD_data(self):
    # Parse file path
    DestFolder, DestFile = os.path.split(self.mhd_file_path)
    FileName, FileExtension = os.path.splitext(DestFile)
    if FileExtension == ".mhd" or FileExtension == ".MHD":
      RAW_File = FileName + ".raw"
    else:
      RAW_File = DestFile + ".raw"
      
    # convert data type
    if self.Image.dtype != "float32":
      self.Image = self.Image.astype("float32")
    
    if self.Image.dtype.byteorder == '>':
      self.Image.byteswap() 
    elif self.Image.dtype.byteorder == '=' and sys.byteorder != "little":
      self.Image.byteswap()
  
    # Write binary file (RAW)
    fid = open(os.path.join(DestFolder, RAW_File),"w") 
    self.Image.transpose(1,0,2).reshape(self.NumVoxels, order='F').tofile(fid)
    fid.close()
          
          
          
