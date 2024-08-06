from __future__ import annotations

__all__ = ['ObjectivesList', 'FidObjective']


import copy
import logging
from enum import Enum

import numpy as np
from typing import Optional, Sequence, Union, Iterable
from scipy import ndimage

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentps.core.data.images._ctImage import CTImage

from opentps.core.data.images._roiMask import ROIMask
from opentps.core.processing.imageProcessing import resampler3D

logger = logging.getLogger(__name__)

class ObjectivesList:
    """
    This class is used to store the objectives of a plan.
    A plan can have multiple objectives.
    An objective can be a Fidelity Objective or an Exotic Objective.

    Attributes
    ----------
    fidObjList: list of FidObjective
        list of Fidelity Objectives
    exoticObjList: list of ExoticObjective
        list of Exotic Objectives
    targetName: str
        name of the target
    targetPrescription: float
        prescription dose of the target
    """
    def __init__(self):
        self.fidObjList:Sequence[FidObjective] = []
        self.exoticObjList = []
        self.targetName:Union[str,Sequence[str]] = []
        self.targetPrescription:Union[float,Sequence[float]] = []
        self.targetMask:Union[ROIMask,Sequence[ROIMask]] = []

    def setTarget(self, roiName, roiMask, prescription):
        """
        Set the targets name and prescription doses (primary + secondary).

        Parameters
        ----------
        roiName: str
            name of the target 
        roiMask: ROIMask
            mask of the target 
        prescription: float
            prescription dose of the target
        """

        self.targetName.append(roiName)
        self.targetMask.append(roiMask)
        self.targetPrescription.append(prescription)

    def append(self, objective):
        """
        Append an objective to the list.

        Parameters
        ----------
        objective: FidObjective or ExoticObjective
            objective to append

        Raises
        -------
        ValueError
            if the objective is not a FidObjective or an ExoticObjective
        """
        if isinstance(objective, FidObjective):
            self.fidObjList.append(objective)
        elif isinstance(objective, ExoticObjective):
            self.exoticObjList.append(objective)
        else:
            raise ValueError(objective.__class__.__name__ + ' is not a valid type for objective')

    def addFidObjective(self, roi, metric, limitValue = None, weight = 1., kind= "Soft", robust = False, volume = None, EUDa = None, fallOffDistance=None, fallOffLowDoseLevel=None, fallOffHighDoseLevel=None):
        """
        Add a Fidelity Objective to the list.

        Parameters
        ----------
        roi: ROIContour or ROIMask
            region of interest
        metric: FidObjective.Metrics or str
            metric to use for the objective : "DMin", "DMax", "DMean", "DUniform", "DVHMin", "DVHMax", "EUDMin", "EUDMax" or "EUDUniform" or "DFALLOFF" or FidObjective.Metrics.DMIN, FidObjective.Metrics.DMAX, FidObjective.Metrics.DMEAN, FidObjective.Metrics.DUNIFORM, FidObjective.Metrics.DVHMIN, FidObjective.Metrics.DVHMAX, FidObjective.Metrics.EUDMIN, FidObjective.Metrics.EUDMAX, FidObjective.Metrics.EUDUNIFORM or FidObjective.Metrics.DFALLOFF
        limitValue: float (default: None) [Gy]
            limit value for the metric
        weight: float (default: 1)
            weight of the objective
        kind: str (default: "Soft")
            kind of the objective : "Soft" or "Hard" (for LP-only)
        robust: bool (default: False)
            if True, the objective is robust
        volume: integer (default : None)
            pourcentage of volume of interest
        EUDa: float (default : None)
            parameter 'a' required for the EUD objectives
        fallOffDistance: float (default : 0.) [cm]
            distance parameter required for the dose fall off objective
        fallOffLowDoseLevel: float (default : 0.) [Gy]
            lower bound dose parameter required for the dose fall off objective
        fallOffHighDoseLevel: float (default : 0.) [Gy]
            higher bound dose parameter required for the dose fall off objective
        Raises
        -------
        ValueError
            if the metric is not supported
            if limitValue is not specified for dose, DVH and EUD objectives
            if volume is not specified for DVH objectives
            if EUDa is not specified for EUD objectives
            if fallOffDistance, fallOffLowDoseLevel and fallOffHighDoseLevel not specified for DFallOff objective

        """
        objective = FidObjective(roi=roi, metric=metric, limitValue=limitValue, weight=weight)
        if metric == FidObjective.Metrics.DMIN.value or metric == FidObjective.Metrics.DMIN:
            objective.metric = FidObjective.Metrics.DMIN
            if limitValue == None: raise Exception("Error: objective DMIN is missing a parameter.")
        elif metric == FidObjective.Metrics.DMAX.value or metric == FidObjective.Metrics.DMAX :
            objective.metric = FidObjective.Metrics.DMAX
            if limitValue == None: raise Exception("Error: objective DMAX is missing a parameter.")
        elif metric == FidObjective.Metrics.DMEAN.value or metric == FidObjective.Metrics.DMEAN :
            objective.metric = FidObjective.Metrics.DMEAN
            if limitValue == None: raise Exception("Error: objective DMEAN is missing a parameter.")
        elif metric == FidObjective.Metrics.DUNIFORM.value or metric == FidObjective.Metrics.DUNIFORM:
            objective.metric = FidObjective.Metrics.DUNIFORM
            if limitValue == None: raise Exception("Error: objective DUNIFORM is missing a parameter.")
        elif metric == FidObjective.Metrics.EUDMAX.value or metric == FidObjective.Metrics.EUDMAX:
            objective.metric = FidObjective.Metrics.EUDMAX
            if EUDa == None or limitValue == None:
                raise Exception("Error: objective EUDMAX is missing a parameter.")
            elif EUDa==0:
                raise Exception("Error: parameter of objective EUDMAX must be different than zero.")
            else :
                objective.EUDa = EUDa
        elif metric == FidObjective.Metrics.EUDMIN.value or metric == FidObjective.Metrics.EUDMIN:
            objective.metric = FidObjective.Metrics.EUDMIN
            if EUDa == None or limitValue == None:
                raise Exception("Error: objective EUDMIN is missing a parameter.")
            elif EUDa==0:
                raise Exception("Error: parameter of objective EUDMAX must be different than zero.")
            else :
                objective.EUDa = EUDa
        elif metric == FidObjective.Metrics.EUDUNIFORM.value or metric == FidObjective.Metrics.EUDUNIFORM:
            objective.metric = FidObjective.Metrics.EUDUNIFORM
            if EUDa == None or limitValue == None:
                raise Exception("Error: objective EUDUNIFORM is missing a parameter.")
            elif EUDa==0:
                raise Exception("Error: parameter of objective EUDMAX must be different than zero.")
            else :
                objective.EUDa = EUDa
        elif metric == FidObjective.Metrics.DVHMAX.value or metric == FidObjective.Metrics.DVHMAX :
            objective.metric = FidObjective.Metrics.DVHMAX
            if volume == None or limitValue == None:
                raise Exception("Error: objective DVHMAX is missing a volume argument.")
            else :
                objective.volume = volume/100
        elif metric == FidObjective.Metrics.DVHMIN.value or metric == FidObjective.Metrics.DVHMIN :
            objective.metric = FidObjective.Metrics.DVHMIN
            if volume == None or limitValue == None:
                raise Exception("Error: objective DVHMIN is missing a volume argument.")
            else :
                objective.volume = volume/100

        elif metric == FidObjective.Metrics.DFALLOFF.value or metric == FidObjective.Metrics.DFALLOFF:
            objective.metric = FidObjective.Metrics.DFALLOFF
            logger.warning("Dose fall-off objective only supported for primary tumor volume at the moment")
            if fallOffDistance == None or fallOffHighDoseLevel == None or fallOffLowDoseLevel == None or self.targetMask is None:
                raise Exception("Error: objective DFALLOFF is missing one or several arguments (falloff distance, lower and higher dose levels).")
            else:
                objective.fallOffDistance = fallOffDistance*10 #(cm->mm)
                objective.fallOffHighDoseLevel = fallOffHighDoseLevel
                objective.fallOffLowDoseLevel = fallOffLowDoseLevel
                
                if self.targetMask:
                    if isinstance(self.targetMask, Iterable):
                        objective.targetMask = copy.deepcopy(self.targetMask[0])
                    else:
                        objective.targetMask = copy.deepcopy(self.targetMask)
                else: raise Exception("Error: Specify targetMask attribut when using DFallOff objective")
        else:
            raise Exception("Error: objective metric " + str(metric) + " is not supported.")

        objective.kind = kind
        objective.robust = robust

        self.fidObjList.append(objective)

    def addExoticObjective(self, weight):
        """
        Add an Exotic Objective to the list.

        Parameters
        ----------
        weight: float
            weight of the objective
        """
        objective = ExoticObjective()
        objective.weight = weight
        self.exoticObjList.append(objective)


class FidObjective:
    """
    This class is used to store a Fidelity Objective.

    Attributes
    ----------
    metric: FitObjective.Metrics
        metric to use for the objective
    limitValue: float (default: 0.)
        limit value for the metric
    weight: float (default: 1.)
        weight of the objective
    robust: bool
        if True, the objective is robust
    kind: str (default: "Soft")
        kind of the objective : "Soft" or "Hard"
    maskVec: np.ndarray
        mask vector
    roi: ROIContour or ROIMask
        region of interest
    roiName: str
        name of the region of interest
    volume: integer (default : None)
            pourcentage of volume of interest
    EUDa: float (default : None)
            parameter 'a' required for the EUD objectives
    """
    class Metrics(Enum):
        DMIN = 'DMin'
        DMAX = 'DMax'
        DMEAN = 'DMean'
        DUNIFORM = 'DUniform'
        DVHMIN = 'DVHMin'
        DVHMAX = 'DVHMax'
        DFALLOFF = 'DFallOff'
        EUDMIN = 'EUDMin'
        EUDMAX = 'EUDMax'
        EUDUNIFORM = 'EUDUniform'

    def __init__(self, roi=None, metric=None, limitValue=0., weight=1., fallOffDistance=0., fallOffLowDoseLevel=0, fallOffHighDoseLevel=100):
        self.metric = metric
        self.limitValue = limitValue
        self.weight = weight
        self.fallOffDistance = fallOffDistance
        self.fallOffLowDoseLevel = fallOffLowDoseLevel
        self.fallOffHighDoseLevel = fallOffHighDoseLevel
        self.voxelwiseLimitValue = []
        self.targetMask = []
        self.robust = False
        self.kind = "Soft"
        self.maskVec = None
        self._roi = roi
        self.volume = None
        self.EUDa = None

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
        
        if self.metric != self.Metrics.DFALLOFF: 
            self.maskVec = np.flip(mask.imageArray, (0, 1))
            self.maskVec = np.ndarray.flatten(self.maskVec, 'F').astype('bool')

        else: 
            # Dose fall off metric calculation
            # resample targetMask
            targetMask = self.targetMask

            if isinstance(targetMask, ROIContour):
                targetMask = targetMask.getBinaryMask(origin=origin, gridSize=gridSize, spacing=spacing)
            elif isinstance(targetMask, ROIMask):
                targetMask = targetMask
                if not (np.array_equal(targetMask.gridSize, gridSize) and
                    np.allclose(targetMask.origin, origin, atol=0.01) and
                    np.allclose(targetMask.spacing, spacing, atol=0.01)):
                    targetMask = resampler3D.resampleImage3D(targetMask, gridSize=gridSize, spacing=spacing, origin=origin)
            
            # TODO: compute euclidean matrix per objective fall-off up to the user-given dose fallOff distance
            euclidDist = ndimage.distance_transform_edt(targetMask.imageArray==0, sampling=spacing)  #sampling to express distance in metric units (mm)
            # Check euclid dist size
            masknan = copy.deepcopy(mask.imageArray)
            masknan[~masknan] = np.nan
            euclidDistROI = euclidDist * masknan

            # Extract voxels within distance in the specified ROI
            voxelsIN = np.logical_and(euclidDistROI > 0, euclidDistROI < self.fallOffDistance) #?
            self.maskVec = np.flip(voxelsIN, (0,1))
            self.maskVec = np.ndarray.flatten(self.maskVec, 'F')

            # get dose rate
            doseRate = (self.fallOffHighDoseLevel - self.fallOffLowDoseLevel) / self.fallOffDistance
            # get reference dose (Dref) as voxel-by-voxel objective
            self.voxelwiseLimitValue = (self.fallOffHighDoseLevel - euclidDistROI * doseRate) #* voxelsIN  #(self.targetPrescription - euclidDistROI * doseRate) #
            self.voxelwiseLimitValue = np.flip(self.voxelwiseLimitValue, (0,1))
            # convert 1D vector
            self.voxelwiseLimitValue = np.ndarray.flatten(self.voxelwiseLimitValue, 'F')
            self.voxelwiseLimitValue = self.voxelwiseLimitValue[self.maskVec]



class ExoticObjective:
    """
    This class is used to store an Exotic Objective.

    Attributes
    ----------
    weight: 
        weight of the objective
    """
    def __init__(self):
        self.weight = ""
