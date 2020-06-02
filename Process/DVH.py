import numpy as np

class DVH:

  def __init__(self, dose, Contour, maxDVH=100.0):
    self.Struct_SeriesInstanceUID = Contour.SeriesInstanceUID
    self.ROIName = Contour.ROIName
    self.Dose_SeriesInstanceUID = dose.SeriesInstanceUID
    self.dose = []
    self.volume = []
    self.Dmean = 0
    self.D98 = 0
    self.D95 = 0
    self.D50 = 0
    self.D5 = 0
    self.D2 = 0
    self.compute_DVH(dose, Contour, maxDVH)


  def compute_Dx(self, x):
    index = np.searchsorted(-self.volume, -x)
    volume = self.volume[index]
    volume2 = self.volume[index+1]
    w2 = (volume-x) / (volume - volume2)
    w1 = (x-volume2) / (volume - volume2)
    return w1*self.dose[index] + w2*self.dose[index+1]


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
    self.volume = h * 100 / np.nanmax(h)

    # compute metrics
    self.Dmean = np.mean(d)
    self.D98 = self.compute_Dx(98)
    self.D95 = self.compute_Dx(95)
    self.D50 = self.compute_Dx(50)
    self.D5 = self.compute_Dx(5)
    self.D2 = self.compute_Dx(2)


