import numpy as np
from typing import Optional


class ObjectivesList:
    def __init__(self):
        self.fidObjList = []
        self.exoticObjList = []
        self.targetName = ""
        self.targetPrescription = 0.0

    def setTarget(self, roiName, prescription):
        self.targetName = roiName
        self.targetPrescription = prescription

    def addFidObjective(self, roiName, metric, condition, limitValue, weight, kind = "Soft", robust=False):
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
            objective.condition = "<"
        elif condition == "GreaterThan" or condition == ">":
            objective.condition = ">"
        else:
            print("Error: objective condition " + condition + " is not supported.")
            return

        objective.limitValue = limitValue
        objective.weight = weight
        objective.kind = kind
        objective.robust = robust

        self.fidObjList.append(objective)

    def initializeContours(self, contours, ct, scoringGridSize: Optional, scoringSpacing: Optional):
        '''I might move this function elsewhere'''
        for objective in self.fidObjList:
            for contour in contours:
                if objective.roiName == contour.name:
                    if scoringSpacing is not None and scoringGridSize is not None:
                        # resample contours
                        objective.maskVec = contour.getBinaryMask(origin=ct.origin, gridSize=scoringGridSize,
                                                                  spacing=scoringSpacing)
                    else:
                        objective.maskVec = contour.getBinaryMask(origin=ct.origin, gridSize=ct.gridSize,
                                                                  spacing=ct.spacing)
                    objective.maskVec = np.flip(objective.maskVec.imageArray, (0, 1))
                    objective.maskVec = np.ndarray.flatten(objective.maskVec, 'F').astype('bool')

    def addExoticObjective(self, weight):
        objective = ExoticObjective()
        objective.weight = weight
        self.exoticObjList.append(objective)


class FidObjective:
    def __init__(self):
        self.roiName = ""
        self.metric = ""
        self.condition = ""
        self.limitValue = ""
        self.weight = ""
        self.robust = False
        self.kind = "Soft"
        self.maskVec = []


class ExoticObjective:
    def __init__(self):
        self.weight = ""
