
class OptimizationObjectives:

  def __init__(self):
    self.list = []
    self.TargetName = ""
    self.TargetPrescription = 0.0
    
    
    
  def setTarget(self, ROIName, Prescription):
    self.TargetName = ROIName
    self.TargetPrescription = Prescription
    
    
    
  def addObjective(self, ROIName, Metric, Condition, LimitValue, Weight):
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
    
    self.list.append(objective)
    
      
    
class OptimizationObjective:

  def __init__(self):
    self.ROIName = ""
    self.Metric = ""
    self.Condition = ""
    self.LimitValue = ""
    self.Weight = ""
    
