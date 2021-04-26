import numpy as np

class DVH:

  def __init__(self, dose=[], Contour=[], maxDVH=100.0):
    self.Struct_SeriesInstanceUID = ""
    self.ROIName = ""
    self.ROIDisplayColor = ""
    self.Dose_SeriesInstanceUID = ""
    self.dose = []
    self.volume = []
    self.volume_absolute = []
    self.Dmean = 0
    self.D98 = 0
    self.D95 = 0
    self.D50 = 0
    self.D5 = 0
    self.D2 = 0
    self.Dmin = 0
    self.Dmax = 0

    if(dose != []):
      self.Dose_SeriesInstanceUID = dose.SeriesInstanceUID

    if(Contour != []):
      self.Struct_SeriesInstanceUID = Contour.SeriesInstanceUID
      self.ROIName = Contour.ROIName
      self.ROIDisplayColor = Contour.ROIDisplayColor

    if(dose != [] and Contour != []):
      self.compute_DVH(dose, Contour, maxDVH)



  def compute_Dx(self, x):
    index = np.searchsorted(-self.volume, -x)
    volume = self.volume[index]
    volume2 = self.volume[index+1]
    if(volume == volume2):
      return self.dose[index]
    else:
      w2 = (volume-x) / (volume - volume2)
      w1 = (x-volume2) / (volume - volume2)
      Dx = w1*self.dose[index] + w2*self.dose[index+1]
      if Dx < 0: Dx = 0
      return Dx


  def compute_DVH(self, dose, Contour, maxDVH=100.0):

    if(dose.Image.shape != Contour.Mask.shape):
      print("ERROR: dose grid size does not match the size of mask \"" + Contour.ROIName + "\". DVH is not computed.")

    number_of_bins = 4096
    DVH_interval = [0, maxDVH]
    bin_size = (DVH_interval[1]-DVH_interval[0])/number_of_bins
    bin_edges = np.arange(DVH_interval[0], DVH_interval[1]+0.5*bin_size, bin_size)
    self.dose = bin_edges[:number_of_bins] + 0.5*bin_size

    d = dose.Image[Contour.Mask]
    h, _ = np.histogram(d, bin_edges)
    h = np.flip(h, 0)
    h = np.cumsum(h)
    h = np.flip(h, 0)
    self.volume = h * 100 / len(d) # volume in %
    self.volume_absolute = h * dose.PixelSpacing[0] * dose.PixelSpacing[1] * dose.PixelSpacing[2] / 1000 # volume in cm3

    # compute metrics
    self.Dmean = np.mean(d)
    self.Dmin = d.min()
    self.Dmax = d.max()
    self.D98 = self.compute_Dx(98)
    self.D95 = self.compute_Dx(95)
    self.D50 = self.compute_Dx(50)
    self.D5 = self.compute_Dx(5)
    self.D2 = self.compute_Dx(2)



class DVH_band:

  def __init__(self):
    self.Struct_SeriesInstanceUID = ""
    self.ROIName = ""
    self.dose = []
    self.volume_low = []
    self.volume_high = []
    self.nominalDVH = []
    self.ROIDisplayColor = []
    self.Dmean = [0, 0]
    self.D98 = [0, 0]
    self.D95 = [0, 0]
    self.D50 = [0, 0]
    self.D5 = [0, 0]
    self.D2 = [0, 0]



  def compute_metrics(self):
    # compute metrics
    self.D98 = self.compute_band_Dx(98)
    self.D95 = self.compute_band_Dx(95)
    self.D50 = self.compute_band_Dx(50)
    self.D5 = self.compute_band_Dx(5)
    self.D2 = self.compute_band_Dx(2)



  def compute_band_Dx(self, x):
    index = np.searchsorted(-self.volume_low, -x)
    volume = self.volume_low[index]
    volume2 = self.volume_low[index+1]
    if(volume == volume2): 
      low_Dx = self.dose[index]
    else:
      w2 = (volume-x) / (volume - volume2)
      w1 = (x-volume2) / (volume - volume2)
      low_Dx = w1*self.dose[index] + w2*self.dose[index+1]
      if low_Dx < 0: low_Dx = 0

    index = np.searchsorted(-self.volume_high, -x)
    volume = self.volume_high[index]
    volume2 = self.volume_high[index+1]
    if(volume == volume2): 
      high_Dx = self.dose[index]
    else:
      w2 = (volume-x) / (volume - volume2)
      w1 = (x-volume2) / (volume - volume2)
      high_Dx = w1*self.dose[index] + w2*self.dose[index+1]
      if high_Dx < 0: high_Dx = 0
    
    return [low_Dx, high_Dx]