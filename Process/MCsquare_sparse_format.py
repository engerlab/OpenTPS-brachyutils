
import os
import numpy as np
import scipy.sparse as sp
import struct
import time
import pickle
import datetime
import struct

try:
  import sparse_dot_mkl
  use_MKL = 1
except:
  use_MKL = 0

class MCsquare_sparse_format:
  
  def __init__(self):
    self.Header_file = ""
    self.Binary_file = ""
    self.Saved_beamlet_file = ""
    self.ImgName = ""
    self.SimulationMode = []
    self.NbrSpots = 0
    self.NbrVoxels = 0
    self.ImageSize = [0, 0, 0]
    self.VoxelSpacing = [1, 1, 1]
    self.Offset = [0, 0, 0]
    self.Image = []
    self.BeamletMatrix = []
    self.Weights = []
    
  def import_Sparse_Beamlets(self, file_path, BeamletRescaling):
    if (not file_path.endswith('.txt')):
      raise NameError('File ', file_path,' is not a valid sparse matrix header')

    try:
      os.path.isfile(file_path)
    except OSError:
      print('File ',file_path, ' not found!')
      return
        

    # Read sparse beamlets header file
    print('Read sparse beamlets: ' , file_path)
    self.Read_Sparse_header(file_path)

    if ('Beamlet' not in self.SimulationMode):
      raise ValueError('Not a beamlet file')
      return
        
    # Read sparse beamlets binary file
    print('Read binary file: ', self.Binary_file)
    self.Read_sparse_data(BeamletRescaling)
    
    
    
  def Read_Sparse_header(self, file_path):

    # Parse file path
    Folder, File = os.path.split(file_path)
    FileName, FileExtension = os.path.splitext(File)
    self.Header_file = file_path
    self.ImgName = FileName

    try:
      with open(self.Header_file,'r') as fid:
        for line in fid:
          if not line.startswith("#"):
            key,val = line.split('=')
            key = key.strip()
            if key == 'NbrSpots':
              self.NbrSpots = int(val)
            elif key == 'ImageSize':
              self.ImageSize = [int(i) for i in val.split()]
              self.NbrVoxels = self.ImageSize[0] * self.ImageSize[1] * self.ImageSize[2]
            elif key == 'VoxelSpacing':
              self.VoxelSpacing = [float(i) for i in val.split()]
            elif key == 'Offset':
              self.Offset = [float(i) for i in val.split()]
            elif key == 'SimulationMode':
              self.SimulationMode.append(val.strip())
            elif key == 'BinaryFile':
              self.Binary_file = os.path.join(Folder, val.strip())
              
    except IOError:
        print('Unable to open file ', self.Header_file)
        
        
  
  def Read_sparse_data(self, BeamletRescaling):
    try:
      fid = open(self.Binary_file,'rb')
    except IOError:
      print('Unable to open file ', self.Binary_file)
      return
      
    buffer_size = 5*self.NbrVoxels
    col_index = np.zeros((buffer_size), dtype=np.uint32)
    row_index = np.zeros((buffer_size), dtype=np.uint32)
    beamlet_data = np.zeros((buffer_size), dtype=np.float32)
    data_id = 0
    last_stacked_col = 0
    num_unstacked_col = 1
    
    time_start = time.time()

    for i in range(self.NbrSpots):
      [NonZeroVoxels] = struct.unpack('I', fid.read(4))
      [BeamID] = struct.unpack('I', fid.read(4))
      [LayerID] = struct.unpack('I', fid.read(4))
      [xcoord] = struct.unpack('<f',fid.read(4))
      [ycoord] = struct.unpack('<f', fid.read(4))
      print("Spot " + str(i) + ": BeamID=" + str(BeamID) + " LayerID=" + str(LayerID) + " Position=(" + str(xcoord) + ";" + str(ycoord) + ") NonZeroVoxels=" + str(NonZeroVoxels))

      if(NonZeroVoxels == 0): continue

      ReadVoxels = 0
      while(1):
        [NbrContinuousValues] = struct.unpack('I',fid.read(4))
        ReadVoxels+=NbrContinuousValues

        [FirstIndex] = struct.unpack('I',fid.read(4))

        for j in range(NbrContinuousValues):
          [temp] = struct.unpack('<f',fid.read(4))
          beamlet_data[data_id] = temp * BeamletRescaling[i]
          row_index[data_id] = FirstIndex+j
          col_index[data_id] = i-last_stacked_col
          data_id += 1

        # temp = np.ndarray((NbrContinuousValues,), '<f', fid.read(4*NbrContinuousValues))
        # beamlet_data[data_id:data_id+NbrContinuousValues] = temp * BeamletRescaling[i]
        # row_index[data_id:data_id+NbrContinuousValues] = list(range(FirstIndex, FirstIndex+NbrContinuousValues))
        # col_index[data_id:data_id+NbrContinuousValues] = i-last_stacked_col
        # data_id += NbrContinuousValues

        if (ReadVoxels >= NonZeroVoxels):
          if i == 0:
            self.BeamletMatrix = sp.csc_matrix((beamlet_data[:data_id], (row_index[:data_id], col_index[:data_id])), shape=(self.NbrVoxels, 1), dtype=np.float32)
            data_id = 0
            last_stacked_col = i+1
            num_unstacked_col = 1
          elif(data_id > buffer_size-self.NbrVoxels):
            A = sp.csc_matrix((beamlet_data[:data_id], (row_index[:data_id], col_index[:data_id])), shape=(self.NbrVoxels, num_unstacked_col), dtype=np.float32)
            data_id = 0
            self.BeamletMatrix = sp.hstack([self.BeamletMatrix, A])
            last_stacked_col = i+1
            num_unstacked_col = 1
          else:
            num_unstacked_col += 1

          break

    # stack last cols  
    A = sp.csc_matrix((beamlet_data[:data_id], (row_index[:data_id], col_index[:data_id])), shape=(self.NbrVoxels, num_unstacked_col-1), dtype=np.float32)
    self.BeamletMatrix = sp.hstack([self.BeamletMatrix, A])
    
    # initialize weights
    self.Weights = np.ones((self.NbrSpots), dtype=np.float32)
    
    print('Beamlets imported in ' + str(time.time()-time_start) + ' sec')
    
    self.print_memory_usage()

    fid.close()
  
  
  
  def print_memory_usage(self):
    if(self.BeamletMatrix == []):
      print(" ")
      print("Beamlets not loaded")
      print(" ")
      
    else:
      mat_size = self.BeamletMatrix.data.nbytes + self.BeamletMatrix.indptr.nbytes + self.BeamletMatrix.indices.nbytes
      print(" ")
      print("Beamlets loaded")
      print("Matrix size: " + str(self.BeamletMatrix.shape))
      print("Non-zero values: " + str(self.BeamletMatrix.nnz))
      print("Data format: " + str(self.BeamletMatrix.dtype))
      print("Memory usage: " + str(mat_size / 1024**3) + " GB")
      print(" ")



  def Compute_dose_from_beamlets(self, Weights=[]):
    self.load()

    if Weights == []:
      Weights = self.Weights

    if use_MKL == 1:
      TotalDose = sparse_dot_mkl.dot_product_mkl(self.BeamletMatrix, Weights)
    else:
      TotalDose = sp.csc_matrix.dot(self.BeamletMatrix, Weights)
    self.unload()
    return TotalDose


      
  def save(self, file_path):
    self.Saved_beamlet_file = file_path
    with open(file_path, 'wb') as fid:
      pickle.dump(self.__dict__, fid, protocol=4)



  def load(self, file_path=""):
    if(file_path == ""):
      file_path = self.Saved_beamlet_file
      
    with open(file_path, 'rb') as fid:
      tmp = pickle.load(fid)

    self.__dict__.update(tmp) 



  def unload(self):
    self.Image = []
    self.BeamletMatrix = []