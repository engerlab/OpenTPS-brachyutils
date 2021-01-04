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
          objective.Mask_vec = np.flip(contour.Mask, (0,1)).transpose(1,0,2)
          objective.Mask_vec = np.ndarray.flatten(objective.Mask_vec, 'F')


  def compute_objective_function(self, x, BLMatrix):
    weights = np.square(x).astype(np.float32)

    if use_MKL == 1:
      doseTotal = sparse_dot_mkl.dot_product_mkl(BLMatrix, weights)
    else:
      doseTotal = sp.csc_matrix.dot(BLMatrix, weights)

    fTot = 0.0

    for objective in self.list:

      if objective.Metric == "Dmax" and objective.Condition == "<":
        f = np.mean(np.maximum(0, doseTotal[objective.Mask_vec]-objective.LimitValue))
      elif objective.Metric == "Dmean" and objective.Condition == "<":
        f = np.maximum(0, np.mean(doseTotal[objective.Mask_vec], dtype=np.float32)-objective.LimitValue)
      elif objective.Metric == "Dmin" and objective.Condition == ">":
        f = np.mean(np.minimum(0, doseTotal[objective.Mask_vec]-objective.LimitValue))

      fTot += objective.Weight * f**2

    return fTot


  def compute_OF_gradient(self, x, BLMatrix,formatArray=32):
    weights = np.square(x).astype(np.float32)
    xDiag = sp.diags(x.astype(np.float32), format='csc')

    if use_MKL == 1:
      doseTotal = sparse_dot_mkl.dot_product_mkl(BLMatrix, weights)
      doseTmp = sparse_dot_mkl.dot_product_mkl(BLMatrix,xDiag)
      dfTot = np.zeros((1, len(x)), dtype=np.float32)
    else:
      doseTotal = sp.csc_matrix.dot(BLMatrix, weights)
      doseTmp = sp.csc_matrix.dot(BLMatrix, xDiag)
      doseTmp = sp.csc_matrix.transpose(doseTmp)
      dfTot = np.zeros((len(x), 1), dtype=np.float32)

    for objective in self.list:

      if objective.Metric == "Dmax" and objective.Condition == "<":
        f = np.maximum(0, doseTotal[objective.Mask_vec]-objective.LimitValue)
        if use_MKL == 1:
          f = sp.diags(f.astype(np.float32), format='csc')
          df = sparse_dot_mkl.dot_product_mkl(f, doseTmp[objective.Mask_vec,:])
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=0)
        else:
          df = sp.csr_matrix.multiply(doseTmp[:,objective.Mask_vec], f)
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=1)

      elif objective.Metric == "Dmean" and objective.Condition == "<":
        f = np.maximum(0, np.mean(doseTotal[objective.Mask_vec], dtype=np.float32)-objective.LimitValue)
        if use_MKL == 1:
          df = sp.csr_matrix.multiply(doseTmp[objective.Mask_vec,:], f)
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=0)
        else:
          df = sp.csr_matrix.multiply(doseTmp[:,objective.Mask_vec], f)
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=1)

      elif objective.Metric == "Dmin" and objective.Condition == ">":
        f = np.minimum(0, doseTotal[objective.Mask_vec]-objective.LimitValue)
        if use_MKL == 1:
          f = sp.diags(f.astype(np.float32), format='csc')
          df = sparse_dot_mkl.dot_product_mkl(f, doseTmp[objective.Mask_vec,:])
          dfTot += objective.Weight * sp.csr_matrix.mean(df, axis=0)
        else:
          df = sp.csr_matrix.multiply(doseTmp[:,objective.Mask_vec], f)
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
