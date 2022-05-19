import numpy as np

class ObjectivesList():
    def __init__(self):
        self.fidObjList = []
        self.exoticObjList = []
        self.targetName = ""
        self.targetPrescription = 0.0

    def setTarget(self, roiName, prescription):
        self.targetName = roiName
        self.targetPrescription = prescription

    def addFidObjective(self, roiName, metric, condition, limitValue, weight, robust=False):
        objective = FidObjective()
        objective.roiName = roiName

        if metric == "Dmin":
            objective.metric = "Dmin"
        elif metric == "Dmax":
            objective.metric = "Dmax"
        elif metric == "Dmean":
            objective.metric = "Dmean"
        else:
            print("Error: objective metric " + metric + " is not supported.")
            return

        if condition == "LessThan" or condition == "<":
            objective.Condition = "<"
        elif condition == "GreaterThan" or condition == ">":
            objective.Condition = ">"
        else:
            print("Error: objective condition " + condition + " is not supported.")
            return

        objective.limitValue = limitValue
        objective.weight = weight
        objective.robust = robust

        self.fidObjList.append(objective)

    def vectorizeContours(self, contours):
        '''I might move this function elsewhere'''
        for objective in self.fidObjList:
            for contour in contours:
                if objective.roiName == contour.ROIName:
                    objective.maskVec = np.flip(contour.mask, (0, 1))
                    objective.maskVec = np.ndarray.flatten(objective.maskVec, 'F')

    def addExoticObjective(self, weight):
        objective = ExoticObjective()
        objective.weight = weight
        self.exoticObjList.append(objective)

class FidObjective:
  def __init__(self):
    self.roiIName = ""
    self.metric = ""
    self.condition = ""
    self.limitValue = ""
    self.weight = ""
    self.robust = False
    self.maskVec = []

class ExoticObjective:
  def __init__(self):
    self.weight = ""


