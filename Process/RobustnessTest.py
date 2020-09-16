import numpy as np
import pickle
import os

from Process.DVH import *

class RobustnessTest:

  def __init__(self):
    self.SelectionStrategy = "Dosimetric"
    self.SetupSystematicError = [1.6, 1.6, 1.6] # mm
    self.SetupRandomError = [1.4, 1.4, 1.4] # mm
    self.RangeSystematicError = 1.6 # %
    self.Target = []
    self.TargetPrescription = 60 # Gy
    self.Nominal = RobustnessScenario()
    self.NumScenarios = 0
    self.Scenarios = []
    self.DVH_bands = []
    self.DoseDistributionType = ""
    self.DoseDistribution = []



  def setNominal(self, dose, contours):
    self.Nominal.Dose = dose
    Target_DVH = DVH(dose, self.Target)
    self.Nominal.Target_D95 = Target_DVH.D95
    self.Nominal.Target_D5 = Target_DVH.D5
    self.Nominal.Target_MSE = self.computeTargetMSE(dose.Image)
    self.Nominal.DVH.clear()
    for contour in contours:
      myDVH = DVH(self.Nominal.Dose, contour)
      self.Nominal.DVH.append(myDVH)
    self.Nominal.Dose.Image = self.Nominal.Dose.Image.astype(np.float32)
    self.Nominal.print_info()


  def addScnenario(self, dose, contours):
    scenario = RobustnessScenario()
    scenario.Dose = dose
    Target_DVH = DVH(dose, self.Target)
    scenario.Target_D95 = Target_DVH.D95
    scenario.Target_D5 = Target_DVH.D5
    scenario.Target_MSE = self.computeTargetMSE(dose.Image)
    scenario.DVH.clear()
    for contour in contours:
      myDVH = DVH(scenario.Dose, contour)
      scenario.DVH.append(myDVH)
    scenario.Dose.Image = scenario.Dose.Image.astype(np.float16) # can be reduced to float16 because all metrics are already computed and it's only used for display
    self.Scenarios.append(scenario)
    self.NumScenarios += 1
    scenario.print_info()



  def recompute_DVH(self, contours):
    self.Nominal.DVH.clear()
    Target_DVH = DVH(self.Nominal.Dose, self.Target)
    self.Nominal.Target_D95 = Target_DVH.D95
    self.Nominal.Target_D5 = Target_DVH.D5
    self.Nominal.Target_MSE = self.computeTargetMSE(self.Nominal.Dose.Image)
    for contour in contours:
      myDVH = DVH(self.Nominal.Dose, contour)
      self.Nominal.DVH.append(myDVH)

    for scenario in self.Scenarios:
      scenario.DVH.clear()
      Target_DVH = DVH(scenario.Dose, self.Target)
      scenario.Target_D95 = Target_DVH.D95
      scenario.Target_D5 = Target_DVH.D5
      scenario.Target_MSE = self.computeTargetMSE(scenario.Dose.Image)
      for contour in contours:
        myDVH = DVH(scenario.Dose, contour)
        scenario.DVH.append(myDVH)



  def computeTargetMSE(self, dose):
    dose_vector = dose[self.Target.Mask]
    error = dose_vector - self.TargetPrescription
    mse = np.mean(np.square(error))
    return mse



  def error_space_analysis(self, metric):
    # sort scenarios from worst to best according to selected metric
    if(metric == "D95"):
      self.Scenarios.sort(key=(lambda scenario: scenario.Target_D95))
    elif(metric == "MSE"):
      self.Scenarios.sort(key=(lambda scenario: scenario.Target_MSE))

    # initialize dose distribution
    if self.DoseDistributionType == "Nominal":
      self.DoseDistribution = self.Nominal.Dose.copy()
    else:
      self.DoseDistribution = self.Scenarios[0].Dose.copy() # Worst scenario

    # initialize dvh-band structure
    all_DVH = []
    all_Dmean = []
    for dvh in self.Scenarios[0].DVH:
      all_DVH.append(np.array([]).reshape((len(dvh.volume), 0)))
      all_Dmean.append([])
      
    # generate DVH-band
    for s in range(self.NumScenarios):
      self.Scenarios[s].selected = 1
      if self.DoseDistributionType == "Voxel wise minimum":
        self.DoseDistribution.Image = np.minimum(self.DoseDistribution.Image, self.Scenarios[s].Dose.Image)
      elif self.DoseDistributionType == "Voxel wise maximum":
        self.DoseDistribution.Image = np.maximum(self.DoseDistribution.Image, self.Scenarios[s].Dose.Image)
      for c in range(len(self.Scenarios[s].DVH)):
          all_DVH[c] = np.hstack((all_DVH[c], np.expand_dims(self.Scenarios[s].DVH[c].volume, axis=1)))
          all_Dmean[c].append(self.Scenarios[s].DVH[c].Dmean)

    self.DVH_bands.clear()
    for c in range(len(self.Scenarios[0].DVH)):
      dvh = self.Scenarios[0].DVH[c]
      dvh_band = DVH_band()
      dvh_band.Struct_SeriesInstanceUID = dvh.Struct_SeriesInstanceUID
      dvh_band.ROIName = dvh.ROIName
      dvh_band.ROIDisplayColor = dvh.ROIDisplayColor
      dvh_band.dose = dvh.dose
      dvh_band.volume_low = np.amin(all_DVH[c], axis=1)
      dvh_band.volume_high = np.amax(all_DVH[c], axis=1)
      dvh_band.nominalDVH = self.Nominal.DVH[c]
      dvh_band.compute_metrics()
      dvh_band.Dmean = [min(all_Dmean[c]), max(all_Dmean[c])]
      self.DVH_bands.append(dvh_band)



  def dosimetric_space_analysis(self, metric, CI):
    if(metric == "D95"):
      self.Scenarios.sort(key=(lambda scenario: scenario.Target_D95))
    elif(metric == "MSE"):
      self.Scenarios.sort(key=(lambda scenario: scenario.Target_MSE))

    start = round(self.NumScenarios * (100-CI) / 100)
    if start == self.NumScenarios: start -= 1

    # initialize dose distribution
    if self.DoseDistributionType == "Nominal":
      self.DoseDistribution = self.Nominal.Dose.copy()
    else:
      self.DoseDistribution = self.Scenarios[start].Dose.copy() # Worst scenario

    # initialize dvh-band structure
    selected_DVH = []
    selected_Dmean = []
    for dvh in self.Scenarios[0].DVH:
      selected_DVH.append(np.array([]).reshape((len(dvh.volume), 0)))
      selected_Dmean.append([])

    # select scenarios
    for s in range(self.NumScenarios):
      if(s < start): 
        self.Scenarios[s].selected = 0
      else: 
        self.Scenarios[s].selected = 1
        if self.DoseDistributionType == "Voxel wise minimum":
          self.DoseDistribution.Image = np.minimum(self.DoseDistribution.Image, self.Scenarios[s].Dose.Image)
        elif self.DoseDistributionType == "Voxel wise maximum":
          self.DoseDistribution.Image = np.maximum(self.DoseDistribution.Image, self.Scenarios[s].Dose.Image)
        for c in range(len(self.Scenarios[s].DVH)):
          selected_DVH[c] = np.hstack((selected_DVH[c], np.expand_dims(self.Scenarios[s].DVH[c].volume, axis=1)))
          selected_Dmean[c].append(self.Scenarios[s].DVH[c].Dmean)

    # compute DVH-band envelopes
    self.DVH_bands.clear()
    for c in range(len(self.Scenarios[s].DVH)):
      dvh = self.Scenarios[0].DVH[c]
      dvh_band = DVH_band()
      dvh_band.Struct_SeriesInstanceUID = dvh.Struct_SeriesInstanceUID
      dvh_band.ROIName = dvh.ROIName
      dvh_band.ROIDisplayColor = dvh.ROIDisplayColor
      dvh_band.dose = dvh.dose
      dvh_band.volume_low = np.amin(selected_DVH[c], axis=1)
      dvh_band.volume_high = np.amax(selected_DVH[c], axis=1)
      dvh_band.nominalDVH = self.Nominal.DVH[c]
      dvh_band.compute_metrics()
      dvh_band.Dmean = [min(selected_Dmean[c]), max(selected_Dmean[c])]
      self.DVH_bands.append(dvh_band)



  def print_info(self):
  	print(" ")
  	print("Nominal scenario:")
  	self.Nominal.print_info()

  	for i in range(len(self.Scenarios)):
  		print("Scenario " + str(i+1))
  		self.Scenarios[i].print_info()



  def save(self, folder_path):
    if not os.path.isdir(folder_path):
      os.mkdir(folder_path)

    for s in range(self.NumScenarios):
      file_path = os.path.join(folder_path, "Scenario_"+str(s)+".tps")
      self.Scenarios[s].save(file_path)

    tmp = self.Scenarios
    self.Scenarios = []

    file_path = os.path.join(folder_path, "RobustnessTest"+".tps")
    with open(file_path, 'wb') as fid:
      pickle.dump(self.__dict__, fid)

    self.Scenarios = tmp


  def load(self, folder_path):
    file_path = os.path.join(folder_path, "RobustnessTest"+".tps")
    with open(file_path, 'rb') as fid:
      tmp = pickle.load(fid)
    self.__dict__.update(tmp) 

    for s in range(self.NumScenarios):
      file_path = os.path.join(folder_path, "Scenario_"+str(s)+".tps")
      scenario = RobustnessScenario()
      scenario.load(file_path)
      self.Scenarios.append(scenario)




class RobustnessScenario:

  def __init__(self):
    self.Dose = []
    self.DVH = []
    self.Target_D95 = 0
    self.Target_D5 = 0
    self.Target_MSE = 0
    self.selected = 0



  def print_info(self):
    print("Target_D95 = " + str(self.Target_D95))
    print("Target_D5 = " + str(self.Target_D5))
    print("Target_MSE = " + str(self.Target_MSE))
    print(" ")



  def save(self, file_path):
    with open(file_path, 'wb') as fid:
      pickle.dump(self.__dict__, fid)



  def load(self, file_path):
    with open(file_path, 'rb') as fid:
      tmp = pickle.load(fid)

    self.__dict__.update(tmp) 