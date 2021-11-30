import numpy as np

class DVH:

  def __init__(self, dose=[], Contour=[], maxDVH=100.0, prescription=None):
    self.Struct_SeriesInstanceUID = ""
    self.ROIName = ""
    self.ROIDisplayColor = ""
    self.LineStyle = "solid"
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
    self.Dstd = 0
    self.prescription = prescription

    if(dose != []):
      self.Dose_SeriesInstanceUID = dose.SeriesInstanceUID

    if(Contour != []):
      self.Struct_SeriesInstanceUID = Contour.SeriesInstanceUID
      self.ROIName = Contour.ROIName
      self.ROIDisplayColor = Contour.ROIDisplayColor

    if(dose != [] and Contour != []):
      self.compute_DVH(dose, Contour, maxDVH)



  def compute_Dx(self, x, return_percentage=False):
    """
    Compute Dx metric (e.g. D95% if x=95, dose that is reveived in at least 95% of the volume)

    Parameters
    ----------
    x: float
      Percentage of volume
    
    return_percentage: bool
      Whether to return the dose in Gy on % of the prescription
    
    Return
    ------
    Dx: float
      Dose received in at least x % of the volume contour

    """
    index = np.searchsorted(-self.volume, -x)
    if(index > len(self.volume)-2): index = len(self.volume)-2
    volume = self.volume[index]
    volume2 = self.volume[index+1]
    if(volume == volume2):
      Dx = self.dose[index]
    else:
      w2 = (volume-x) / (volume - volume2)
      w1 = (x-volume2) / (volume - volume2)
      Dx = w1*self.dose[index] + w2*self.dose[index+1]
      if Dx < 0: Dx = 0

    if return_percentage:
      assert self.prescription is not None
      return (Dx / self.prescription) * 100
    return Dx
    

  def compute_Dcc(self, x, return_percentage=False):
    """
    Compute Dcc metric (e.g. D200cc if x=200 for minimal dose that is received the most irradiated 200cm^3)

    Parameters
    ----------
    x: float
      Volume in cm^3

    return_percentage: bool
      Whether to return the dose in Gy on % of the prescription
    
    Return
    ------
    Dcc: float
      Dose received

    """
    index = np.searchsorted(-self.volume_absolute, -x)
    if(index > len(self.volume)-2): index = len(self.volume)-2
    volume = self.volume_absolute[index]
    volume2 = self.volume_absolute[index+1]
    if(volume == volume2):
      Dcc = self.dose[index]
    else:
      w2 = (volume-x) / (volume - volume2)
      w1 = (x-volume2) / (volume - volume2)
      Dcc = w1*self.dose[index] + w2*self.dose[index+1]
      if Dcc < 0: Dcc = 0
    
    if return_percentage:
      assert self.prescription is not None
      return (Dcc / self.prescription) * 100
    return Dcc


  def compute_Vg(self, x, return_percentage=True):
    """
    Compute Vg metric (e.g. V5 if x=5: volume that received at least 5Gy)

    Parameters
    ----------
    x: float
      Dose in Gy

    return_percentage: bool
      Whether to return the volume in percentage or in cm^3
    
    Return
    ------
    out: float
      Volume that receives at least x Gy

    """
    index = np.searchsorted(self.dose, x)
    if return_percentage: return self.volume[index]
    else: return self.volume_absolute[index]


  def compute_Vx(self, x, return_percentage=True):
    """
    Compute Vx metric (e.g. V95% if x=95: volume that received at least 95% of the prescription)

    Parameters
    ----------
    x: float
      Dose in % of prescription

    return_percentage: bool
      Whether to return the volume in percentage or in cm^3
    
    Return
    ------
    out: float
      Return volume that receives at least x % of the prescribed dose

    """
    assert self.prescription is not None
    dose_percentage = (self.dose / self.prescription) * 100 
    index = np.searchsorted(dose_percentage, x)
    if return_percentage:
      return self.volume[index]
    else:
      return self.volume_absolute[index]
      

  def compute_DVH(self, dose, Contour, maxDVH=100.0):

    if(dose.Image.shape != Contour.Mask.shape):
      print("ERROR: dose grid size does not match the size of mask \"" + Contour.ROIName + "\". DVH is not computed.")

    number_of_bins = 4096
    DVH_interval = [0, maxDVH]
    bin_size = (DVH_interval[1]-DVH_interval[0])/number_of_bins
    bin_edges = np.arange(DVH_interval[0], DVH_interval[1]+0.5*bin_size, bin_size)
    bin_edges[-1] = maxDVH + dose.Image.max()
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
    self.Dstd = np.std(d)
    self.Dmin = d.min() if len(d)>0 else 0
    self.Dmax = d.max() if len(d)>0 else 0
    self.D98 = self.compute_Dx(98)
    self.D95 = self.compute_Dx(95)
    self.D50 = self.compute_Dx(50)
    self.D5 = self.compute_Dx(5)
    self.D2 = self.compute_Dx(2)


  def homogeneity_index(self, method='Yan_2019'):
    """
    Compute the homogeneity index of the contour

    Parameters
    ----------
    method: str
      Type of method for the computation. 
      'conventional_1' and 'conventional_2' are conventional method based on the DVH metrics. 
      'S-index' is the standard deviation of the dose. (see https://doi.org/10.1120/jacmp.v8i2.2390)
      'Yan_2019' comes from https://doi.org/10.1002/acm2.12739 
      It is based on the area under an ideal dose-volume histogram curve (IA), 
      the area under the achieved dose-volume histogram curve (AA), and the overlapping area between the IA and AA (OA). 
      It is defined as the ratio of the square of OA to the product of the IA and AA.

    Return
    ------
    out: float
      Homogenity index

    """
    if method == 'conventional_1':
      assert self.prescription is not None
      return (self.D2 - self.D98) / self.prescription

    if method == 'conventional_2':
      return (self.D2 - self.D98) / self.D50

    if method == 'conventional_3':
      assert self.prescription is not None
      return self.Dmax / self.prescription

    if method == 'S-index':
      return self.Dstd

    if method == 'Yan_2019':
      assert self.prescription is not None
      index = np.searchsorted(self.dose, self.prescription)
      IA = self.dose[index-1] * 100. # area under ideal DVH (step function)
      AA = np.trapz(y=self.volume, x=self.dose) # area under achieved DVH
      OA = np.trapz(y=self.volume[:index], x=self.dose[:index]) # overlapping area between IA and AA.
      assert OA <= IA # cannot do better than the step function
      return OA**2 / (IA * AA)

    raise NotImplementedError(f'Homogenity index method {method} not implemented.')


  def conformity_index(self, dose, Contour, body_contour, method="Paddick"):
    """
    Compute the conformity index describing how tightly the prescription dose is conforming to the target.

    Parameters
    ----------

    dose: RTdose
      The RTdose object

    Contour: ROIcontour
      ROIcontour object of the target

    body_contour: ROIcontour
      ROIcontour object of delineating the contour of the body of the patient

    method: str
      Method to use for computing the conformity index
      if method=='RTOG': use the Radiation therapy oncology group guidelines index (https://doi.org/10.1016/0360-3016(93)90548-A)
      if method=='Paddick': use Paddick index, improved RTOG by taking into account the location and shape of the prescription 
      isodose with respect to the target volume (https://doi.org/10.3171/sup.2006.105.7.194)

    Return
    ------
    out: float
      Conformity index

    """
    assert self.prescription is not None
    percentile = 0.95 # ICRU reference isodose
    if method=='RTOG': # Radiation therapy oncology group guidelines (1993)
      # prescription isodose volume
      isodose_prescription_volume = np.sum(dose.Image[body_contour.Mask==1] >= percentile*self.prescription)
      contour_volume = np.sum(Contour.Mask)
      return isodose_prescription_volume / contour_volume

    if method == 'Paddick':
      # prescription isodose volume
      isodose_prescription_volume = np.sum(dose.Image[body_contour.Mask==1] >= percentile*self.prescription)
      # Target volume
      contour_volume = np.sum(Contour.Mask)
      # target volume covered by the prescription isodose volume
      contour_volume_covered_by_prescription = np.sum(dose.Image[Contour.Mask == 1] >= percentile*self.prescription)
      return contour_volume_covered_by_prescription**2 / (isodose_prescription_volume * contour_volume)

    raise NotImplementedError(f'Conformity index method {method} not implemented.')


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
    if(index > len(self.volume_low)-2): index = len(self.volume_low)-2
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
    if(index > len(self.volume_high)-2): index = len(self.volume_high)-2
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



