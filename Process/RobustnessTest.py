import numpy as np
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
		self.Scenarios = []



	def setNominal(self, dose):
		self.Nominal.Dose = dose
		Target_DVH = DVH(dose, self.Target)
		self.Nominal.DVH.append(Target_DVH)
		self.Nominal.Target_D95 = Target_DVH.D95
		self.Nominal.Target_D5 = Target_DVH.D5
		self.Nominal.Target_MSE = self.computeTargetMSE(dose.Image)
		self.Nominal.print_info()


	def addScnenario(self, dose):
		scenario = RobustnessScenario()
		scenario.Dose = dose
		Target_DVH = DVH(dose, self.Target)
		scenario.DVH.append(Target_DVH)
		scenario.Target_D95 = Target_DVH.D95
		scenario.Target_D5 = Target_DVH.D5
		scenario.Target_MSE = self.computeTargetMSE(dose.Image)
		self.Scenarios.append(scenario)
		scenario.print_info()



	def computeTargetMSE(self, dose):
		dose_vector = dose[self.Target.Mask]
		error = dose_vector - self.TargetPrescription
		mse = np.mean(np.square(error))
		return mse



class RobustnessScenario:

	def __init__(self):
		self.Dose = []
		self.DVH = []
		self.Target_D95 = 0
		self.Target_D5 = 0
		self.Target_MSE = 0

	def print_info(self):
		print("Target_D95 = " + str(self.Target_D95))
		print("Target_D5 = " + str(self.Target_D5))
		print("Target_MSE = " + str(self.Target_MSE))
		print(" ")