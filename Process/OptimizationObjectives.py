import numpy as np
import scipy.sparse as sp
import time
import os
import pickle

try:
  import sparse_dot_mkl
  use_MKL = 1
except:
  use_MKL = 0


class OptimizationObjectives:

  def __init__(self):
    self.list = []
    self.TargetName = ""
    self.TargetPrescription = 0.0



  def setTarget(self, ROIName, Prescription):
    self.TargetName = ROIName
    self.TargetPrescription = Prescription



  def addObjective(self, ROIName, Metric, Condition, LimitValue, Weight, Robust=False):
    objective = OptimizationObjective()
    objective.ROIName = ROIName

    if Metric == "Dmin": objective.Metric = "Dmin"
    elif Metric == "Dmax": objective.Metric = "Dmax"
    elif Metric == "Dmean": objective.Metric = "Dmean"
    else:
      print("Error: objective metric " + Metric + " is not supported.")
      return

    if Condition == "LessThan" or Condition == "<": objective.Condition = "<"
    elif Condition == "GreaterThan" or Condition == ">": objective.Condition = ">"
    else:
      print("Error: objective condition " + Condition + " is not supported.")
      return

    objective.LimitValue = LimitValue
    objective.Weight = Weight
    objective.Robust = Robust

    self.list.append(objective)



  def initialize_objective_function(self, contours):
    for objective in self.list:
      for contour in contours:
        if objective.ROIName == contour.ROIName:
          # vectorize contour
          objective.Mask_vec = np.flip(contour.Mask, (0,1))
          objective.Mask_vec = np.ndarray.flatten(objective.Mask_vec, 'F')


  def compute_objective_function(self, x, BLMatrix, ScenariosBL=[], ReturnWorstCase=False):
    weights = np.square(x).astype(np.float32)

    fTot = 0.0
    fTotScenario = 0.0
    ScenarioList = []


    # compute objectives for nominal scenario
    if use_MKL == 1:
      doseTotal = sparse_dot_mkl.dot_product_mkl(BLMatrix, weights)
    else:
      doseTotal = sp.csc_matrix.dot(BLMatrix, weights)

    for objective in self.list:
      if objective.Metric == "Dmax" and objective.Condition == "<":
        f = np.mean(np.maximum(0, doseTotal[objective.Mask_vec]-objective.LimitValue)**2)
      elif objective.Metric == "Dmean" and objective.Condition == "<":
        f = np.maximum(0, np.mean(doseTotal[objective.Mask_vec], dtype=np.float32)-objective.LimitValue)**2
      elif objective.Metric == "Dmin" and objective.Condition == ">":
        f = np.mean(np.minimum(0, doseTotal[objective.Mask_vec]-objective.LimitValue)**2)

      if objective.Robust == False: fTot += objective.Weight * f
      else: fTotScenario += objective.Weight * f

    ScenarioList.append(fTotScenario)


    # skip calculation of error scenarios if there is no robust objective
    robust = False
    for objective in self.list:
      if objective.Robust == True: robust = True

    if(ScenariosBL==[] or robust == False): 
      if(ReturnWorstCase == False): return fTot
      else: return fTot, -1 # returns id of the worst case scenario (-1 for nominal)


    # Compute objectives for error scenarios
    for ScenarioBL in ScenariosBL:
      fTotScenario = 0.0

      if use_MKL == 1:
        doseTotal = sparse_dot_mkl.dot_product_mkl(ScenarioBL.BeamletMatrix, weights)
      else:
        doseTotal = sp.csc_matrix.dot(ScenarioBL.BeamletMatrix, weights)

      for objective in self.list:
        if objective.Robust == False: continue

        if objective.Metric == "Dmax" and objective.Condition == "<":
          f = np.mean(np.maximum(0, doseTotal[objective.Mask_vec]-objective.LimitValue)**2)
        elif objective.Metric == "Dmean" and objective.Condition == "<":
          f = np.maximum(0, np.mean(doseTotal[objective.Mask_vec], dtype=np.float32)-objective.LimitValue)**2
        elif objective.Metric == "Dmin" and objective.Condition == ">":
          f = np.mean(np.minimum(0, doseTotal[objective.Mask_vec]-objective.LimitValue)**2)

        fTotScenario += objective.Weight * f

      ScenarioList.append(fTotScenario)

    fTot += max(ScenarioList)

    if(ReturnWorstCase == False): return fTot
    else: return fTot, ScenarioList.index(max(ScenarioList))-1 # returns id of the worst case scenario (-1 for nominal)


  def compute_OF_gradient(self, x, BLMatrix, ScenariosBL=[], formatArray=32):
    # get worst case scenario
    if(ScenariosBL!=[]): fTot, WorstCase = self.compute_objective_function(x, BLMatrix, ScenariosBL=ScenariosBL, ReturnWorstCase=True)
    else: WorstCase = -1

    weights = np.square(x).astype(np.float32)
    xDiag = sp.diags(x.astype(np.float32), format='csc')

    if use_MKL == 1:
      doseNominal = sparse_dot_mkl.dot_product_mkl(BLMatrix, weights)
      doseNominalBL = sparse_dot_mkl.dot_product_mkl(BLMatrix,xDiag)
      if(WorstCase != -1):
        doseScenario = sparse_dot_mkl.dot_product_mkl(ScenariosBL[WorstCase].BeamletMatrix, weights)
        doseScenarioBL = sparse_dot_mkl.dot_product_mkl(ScenariosBL[WorstCase].BeamletMatrix,xDiag)
      dfTot = np.zeros((1, len(x)), dtype=np.float32)

    else:
      doseNominal = sp.csc_matrix.dot(BLMatrix, weights)
      doseNominalBL = sp.csc_matrix.dot(BLMatrix, xDiag)
      doseNominalBL = sp.csc_matrix.transpose(doseNominalBL)
      if(WorstCase != -1):
        doseScenario = sp.csc_matrix.dot(ScenariosBL[WorstCase].BeamletMatrix, weights)
        doseScenarioBL = sp.csc_matrix.dot(ScenariosBL[WorstCase].BeamletMatrix, xDiag)
        doseScenarioBL = sp.csc_matrix.transpose(doseScenarioBL)
      dfTot = np.zeros((len(x), 1), dtype=np.float32)

    for objective in self.list:
      if(WorstCase != -1 and objective.Robust == True):
        doseTotal = doseScenario
        doseBL = doseScenarioBL
      else:
        doseTotal = doseNominal
        doseBL = doseNominalBL

      if objective.Metric == "Dmax" and objective.Condition == "<":
        f = np.maximum(0, doseTotal[objective.Mask_vec]-objective.LimitValue)
        if use_MKL == 1:
          f = sp.diags(f.astype(np.float32), format='csc')
          df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.Mask_vec,:])
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=0)
        else:
          df = sp.csr_matrix.multiply(doseBL[:,objective.Mask_vec], f)
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=1)

      elif objective.Metric == "Dmean" and objective.Condition == "<":
        f = np.maximum(0, np.mean(doseTotal[objective.Mask_vec], dtype=np.float32)-objective.LimitValue)
        if use_MKL == 1:
          df = sp.csr_matrix.multiply(doseBL[objective.Mask_vec,:], f)
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=0)
        else:
          df = sp.csr_matrix.multiply(doseBL[:,objective.Mask_vec], f)
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=1)

      elif objective.Metric == "Dmin" and objective.Condition == ">":
        f = np.minimum(0, doseTotal[objective.Mask_vec]-objective.LimitValue)
        if use_MKL == 1:
          f = sp.diags(f.astype(np.float32), format='csc')
          df = sparse_dot_mkl.dot_product_mkl(f, doseBL[objective.Mask_vec,:])
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=0)
        else:
          df = sp.csr_matrix.multiply(doseBL[:,objective.Mask_vec], f)
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=1)

    dfTot = 4 * dfTot
    dfTot = np.squeeze(np.asarray(dfTot)).astype(np.float64)
    #if scipy-lbfgs used, need to use float64
    if formatArray==64:
        dfTot = np.array(dfTot, dtype ="float64")

    return dfTot



class OptimizationObjective:

  def __init__(self):
    self.ROIName = ""
    self.Metric = ""
    self.Condition = ""
    self.LimitValue = ""
    self.Weight = ""
    self.Robust = False
    self.Mask_vec = []



class ObjectiveTemplateList:

  def __init__(self):
    self.list = []
    self.SelectedID = -1
    self.saved_file = "./Objective_Templates.dat"

    self.LoadTemplates()


  def LoadTemplates(self):
    if os.path.isfile(self.saved_file):
      with open(self.saved_file, 'rb') as fid:
        self.list = pickle.load(fid)


  def SaveTemplates(self):
    with open(self.saved_file, 'wb') as fid:
      pickle.dump(self.list, fid)



class ObjectiveTemplate:

  def __init__(self):
    self.Name = ""
    self.Objectives = []
