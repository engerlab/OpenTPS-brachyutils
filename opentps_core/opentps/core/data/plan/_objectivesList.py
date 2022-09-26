from __future__ import annotations

__all__ = ['ObjectivesList', 'FidObjective']


from enum import Enum

import numpy as np
from typing import Optional, Sequence

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentps.core.data.images._ctImage import CTImage

from opentps.core.data.images._roiMask import ROIMask
from opentps.core.processing.imageProcessing import resampler3D

class ObjectivesList:
    def __init__(self):
        self.fidObjList:Sequence[FidObjective] = []
        self.exoticObjList = []
        self.targetName = ""
        self.targetPrescription = 0.0

        self._scoringOrigin = np.array((0, 0, 0))
        self._scoringGridSize = None
        self._scoringSpacing = np.array((1, 1, 1))

    @property
    def scoringOrigin(self) -> Sequence[float]:
        return self._scoringOrigin

    @property
    def scoringGridSize(self) -> Sequence[int]:
        return self._scoringGridSize

    @property
    def scoringSpacing(self) -> Sequence[float]:
        return self._scoringSpacing

    def setTarget(self, roiName, prescription):
        self.targetName = roiName
        self.targetPrescription = prescription

    def append(self, objective):
        if isinstance(objective, FidObjective):
            self.fidObjList.append(objective)
        elif isinstance(objective, ExoticObjective):
            self.exoticObjList.append(objective)
        else:
            raise ValueError(objective.__class__.__name__ + ' is not a valid type for objective')

    def addFidObjective(self, roi, metric, limitValue, weight, kind="Soft", robust=False):
        objective = FidObjective(roi=roi, metric=metric, limitValue=limitValue, weight=weight)

        if metric == FidObjective.Metrics.DMIN:
            objective.metric = FidObjective.Metrics.DMIN
        elif metric == FidObjective.Metrics.DMAX:
            objective.metric = FidObjective.Metrics.DMAX
        elif metric == FidObjective.Metrics.DMEAN:
            objective.metric = FidObjective.Metrics.DMEAN
        else:
            print("Error: objective metric " + str(metric) + " is not supported.")
            return

        objective.kind = kind
        objective.robust = robust
        objective.setScoringParameters(self.scoringSpacing, self.scoringGridSize, self.scoringOrigin)

        self.fidObjList.append(objective)

    def setScoringParameters(self, ct:CTImage, scoringGridSize:Optional[Sequence[int]]=None, scoringSpacing:Optional[Sequence[float]]=None):
        self._scoringOrigin = ct.origin

        if scoringGridSize is None:
            scoringGridSize = ct.gridSize
        self._scoringGridSize = scoringGridSize

        if scoringSpacing is None:
            scoringSpacing = ct.spacing
        self._scoringSpacing = scoringSpacing

        for objective in self.fidObjList:
            objective.setScoringParameters(self._scoringSpacing, self._scoringGridSize, self._scoringOrigin)

    def addExoticObjective(self, weight):
        objective = ExoticObjective()
        objective.weight = weight
        self.exoticObjList.append(objective)


class FidObjective:
    class Metrics(Enum):
        DMIN = 'DMin'
        DMAX = 'DMax'
        DMEAN = 'DMean'

    def __init__(self, roi=None, metric=None, limitValue=0., weight=1.):
        self.metric = metric
        self.limitValue = limitValue
        self.weight = weight
        self.robust = False
        self.kind = "Soft"
        self.maskVec = None

        self._roi = None
        self._scoringOrigin = np.array((0, 0, 0))
        self._scoringGridSize = None
        self._scoringSpacing = np.array((1, 1, 1))

        self.roi = roi

    @property
    def roi(self):
        return self._roi

    @roi.setter
    def roi(self, roi):
        self._roi = roi

        if not (self._scoringGridSize is None):
            self._updateMaskVec()

    @property
    def roiName(self) -> str:
        return self.roi.name

    @property
    def scoringOrigin(self) -> Sequence[float]:
        return self._scoringOrigin

    @property
    def scoringGridSize(self) -> Sequence[int]:
        return self._scoringGridSize

    @property
    def scoringSpacing(self) -> Sequence[float]:
        return self._scoringSpacing

    def setScoringParameters(self, spacing:Sequence[float], gridSize:Sequence[int], origin:Sequence[float]):
        self._scoringSpacing = spacing
        self._scoringGridSize = gridSize
        self._scoringOrigin = origin

        self._updateMaskVec()

    def _updateMaskVec(self):
        from opentps.core.data._roiContour import ROIContour

        if self.scoringGridSize is None:
            raise Exception("scoringGridSize not set")

        if isinstance(self.roi, ROIContour):
            mask = self.roi.getBinaryMask(origin=self.scoringOrigin, gridSize=self.scoringGridSize, spacing=self.scoringSpacing)
        elif isinstance(self.roi, ROIMask):
            mask = resampler3D.resampleImage3D(self.roi, gridSize=self.scoringGridSize, spacing=self.scoringSpacing, origin=self.scoringOrigin)
        else:
            raise Exception(self.roi.__class__.__name__ + ' is not a supported class for roi')

        self.maskVec = np.flip(mask.imageArray, (0, 1))
        self.maskVec = np.ndarray.flatten(self.maskVec, 'F').astype('bool')

class ExoticObjective:
    def __init__(self):
        self.weight = ""
