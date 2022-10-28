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

        self._scoringOrigin = None
        self._scoringGridSize = None
        self._scoringSpacing = None

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
        if self.scoringSpacing is not None and self.scoringGridSize is not None and self.scoringOrigin is not None:
            objective._updateMaskVec(spacing=self.scoringSpacing, gridSize=self.scoringGridSize, origin=self.scoringOrigin)

        self.fidObjList.append(objective)

    def setScoringParameters(self, ct:CTImage, scoringGridSize:Optional[Sequence[int]]=None, scoringSpacing:Optional[Sequence[float]]=None):
        self._scoringOrigin = ct.origin

        # spacing is None
        if scoringSpacing is None:
            if scoringGridSize is None:
                scoringGridSize = ct.gridSize
            scoringSpacing = ct.spacing*ct.gridSize/scoringGridSize
        else:
            if np.isscalar(scoringSpacing):
                scoringSpacing = scoringSpacing*np.ones(ct.spacing.shape)
            # gridSize is None but spacing is not
            if scoringGridSize is None:
                scoringGridSize = np.floor(ct.gridSize*ct.spacing/scoringSpacing)
        self._scoringGridSize = scoringGridSize
        self._scoringSpacing = scoringSpacing

        for objective in self.fidObjList:
            objective._updateMaskVec(self._scoringSpacing, self._scoringGridSize, self._scoringOrigin)

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
        self._roi = roi

    @property
    def roi(self):
        return self._roi

    @roi.setter
    def roi(self, roi):
        self._roi = roi

    @property
    def roiName(self) -> str:
        return self.roi.name


    def _updateMaskVec(self, spacing:Sequence[float], gridSize:Sequence[int], origin:Sequence[float]):
        from opentps.core.data._roiContour import ROIContour

        if isinstance(self.roi, ROIContour):
            mask = self.roi.getBinaryMask(origin=origin, gridSize=gridSize, spacing=spacing)
        elif isinstance(self.roi, ROIMask):
            mask = self.roi
            if not (np.array_equal(mask.gridSize, gridSize) and
                np.allclose(mask.origin, origin, atol=0.01) and
                np.allclose(mask.spacing, spacing, atol=0.01)):
                mask = resampler3D.resampleImage3D(self.roi, gridSize=gridSize, spacing=spacing, origin=origin)
        else:
            raise Exception(self.roi.__class__.__name__ + ' is not a supported class for roi')

        self.maskVec = np.flip(mask.imageArray, (0, 1))
        self.maskVec = np.ndarray.flatten(self.maskVec, 'F').astype('bool')


class ExoticObjective:
    def __init__(self):
        self.weight = ""
