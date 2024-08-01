
__all__ = ['PlanDesign','Robustness']

import logging
import time
from typing import Optional, Sequence, Union, Iterable
from enum import Enum
import numpy as np
import pydicom

from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data._roiContour import ROIContour
from opentps.core.data.images import CTImage
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.plan._rangeShifter import RangeShifter
from opentps.core.processing.imageProcessing import resampler3D
from opentps.core.data._patientData import PatientData
from opentps.core.data.plan import ObjectivesList
from opentps.core.processing.planEvaluation.robustnessEvaluation import RobustnessEval
from opentps.core.processing.planOptimization.planInitializer import PlanInitializer

logger = logging.getLogger(__name__)


class PlanDesign(PatientData):
    """
    This class is used to store the plan design. It inherits from PatientData.

    Attributes
    ----------
    spotSpacing: float (default: 5.0)
        spacing between spots in mm
    layerSpacing: float (default: 5.0)
        spacing between layers in mm
    targetMargin: float (default: 5.0)
        margin around the target in mm
    scoringVoxelSpacing: float or list of float
        spacing of the scoring grid in mm
    targetMask: ROIMask
        union of target masks
    proximalLayers: int (default: 1)
        number of proximal layers
    distalLayers: int (default: 1)
        number of distal layers
    layersToSpacingAlignment: bool (default: False)
        if True, the spacing between layers is aligned with the scoring grid
    calibration: AbstractCTCalibration
        calibration of the CT for stopping power conversion
    ct: CTImage (default: None)
        CT image
    beamNames: list of str
        list of beam names
    gantryAngles: list of float
        list of gantry angles
    couchAngles: list of float
        list of couch angles
    rangeShifters: list of RangeShifter
        list of range shifters
    objectives: ObjectivesList
        list of objectives
    beamlets: list of Beamlet
        list of beamlets
    beamletsLET: list of Beamlet
        list of beamlets with LET
    robustness: Robustness
        robustness evaluation
    """
    def __init__(self):
        super().__init__()

        self.spotSpacing = 5.0
        self.layerSpacing = 5.0
        self.targetMargin = 5.0
        self._scoringVoxelSpacing = None
        self._scoringGridSize = None
        self._scoringOrigin = None
        self.proximalLayers = 1
        self.distalLayers = 1
        self.layersToSpacingAlignment = False
        self.calibration: AbstractCTCalibration = None
        self.ct: CTImage = None
        self.beamNames = []
        self.gantryAngles = []
        self.couchAngles = []
        self.rangeShifters: Sequence[RangeShifter] = []

        self.objectives = ObjectivesList()
        self.beamlets = []
        self.beamletsLET = []

        self.robustness = Robustness()
        self.robustnessEval = RobustnessEval()

    @property
    def scoringVoxelSpacing(self) -> Sequence[float]:
        if self._scoringVoxelSpacing is not None:
            return self._scoringVoxelSpacing
        else:
            return self.ct.spacing

    @scoringVoxelSpacing.setter
    def scoringVoxelSpacing(self, spacing: Union[float, Sequence[float]]):
        if np.isscalar(spacing):
            self._scoringVoxelSpacing = np.array([spacing, spacing, spacing])
        else:
            self._scoringVoxelSpacing = np.array(spacing)

    @property
    def scoringGridSize(self):
        if self._scoringGridSize is not None:
            return self._scoringGridSize
        else:
            return self.ct.gridSize
    
    @scoringGridSize.setter
    def scoringGridSize(self, gridSize: Sequence[float]):
        self._scoringGridSize = gridSize

    @property
    def scoringOrigin(self):
        if self._scoringOrigin is not None:
            return self._scoringOrigin
        else:
            return self.ct.origin
        
    @scoringOrigin.setter
    def scoringOrigin(self, origin):
        self._scoringOrigin = origin


    def buildPlan(self):
        """
        Builds a plan from the plan design

        Returns
        --------
        RTPlan
            plan
        """
        start = time.time()
        # Spot placement
        from opentps.core.data.plan import RTPlan
        plan = RTPlan("NewPlan")
        plan.SOPInstanceUID = pydicom.uid.generate_uid()
        plan.seriesInstanceUID = plan.SOPInstanceUID + ".1"
        plan.modality = "Ion therapy"
        plan.radiationType = "Proton"
        plan.scanMode = "MODULATED"
        plan.treatmentMachineName = "Unknown"
        logger.info('Building plan ...')
        self.createBeams(plan)
        self.initializeBeams(plan)
        plan.planDesign = self
        for beam in plan.beams:
            beam.reorderLayers('decreasing')

        logger.info("New plan created in {} sec".format(time.time() - start))
        logger.info("Number of spots: {}".format(plan.numberOfSpots))

        return plan
    
    def defineTargetMaskAndPrescriptionFromObjList(self):
        """
        Defines the target mask and the prescription from the objective list 
        Only works if objectives have already been set.
        """
        from opentps.core.data._roiContour import ROIContour

        targetMask = None
        for objective in self.objectives.fidObjList:
            if objective.metric == objective.Metrics.DMIN:
                roi = objective.roi

                if isinstance(roi, ROIContour):
                    mask = roi.getBinaryMask(origin=self.ct.origin, gridSize=self.ct.gridSize,
                                             spacing=self.ct.spacing)
                elif isinstance(roi, ROIMask):
                    mask = resampler3D.resampleImage3D(roi, origin=self.ct.origin,
                                                       gridSize=self.ct.gridSize,
                                                       spacing=self.ct.spacing)
                else:
                    raise Exception(roi.__class__.__name__ + ' is not a supported class for roi')

                if targetMask is None:
                    targetMask = mask
                else:
                    targetMask.imageArray = np.logical_or(targetMask.imageArray, mask.imageArray)
                
                self.objectives.setTarget(objective.roiName, mask, objective.limitValue)

        if targetMask is None:
            raise Exception('Could not find a target volume in dose fidelity objectives')

        self.targetMask = targetMask

    def defineTargetMaskAndPrescription(self,target:Union[Union[ROIMask,ROIContour],Sequence[Union[ROIMask,ROIContour]]],targetPrescription:Union[float,Sequence[float]]):
        """
        Defines the target mask and the prescription with given parameters (primary and secondary tumors masl)
        Works even if no objectives have been set (at the plan design stage)
        Call required before spot placement.
        """
        from opentps.core.data._roiContour import ROIContour
        targetMask = None
        if isinstance(target,Iterable):
            for target,p in list(zip(target,targetPrescription)):                
                if isinstance(target, ROIContour):
                        mask = target.getBinaryMask(origin=self.ct.origin, gridSize=self.ct.gridSize,
                                                spacing=self.ct.spacing)
                elif isinstance(target, ROIMask):
                    mask = resampler3D.resampleImage3D(target, origin=self.ct.origin,
                                                    gridSize=self.ct.gridSize,
                                                    spacing=self.ct.spacing)
                else:
                    raise Exception(target.__class__.__name__ + ' is not a supported class for roi')

                if targetMask is None:
                    targetMask = mask
                else:
                    targetMask.imageArray = np.logical_or(targetMask.imageArray, mask.imageArray)
                
                self.objectives.setTarget(target.name, mask, p)
        else:
            if isinstance(target, ROIContour):
                    mask = target.getBinaryMask(origin=self.ct.origin, gridSize=self.ct.gridSize,
                                            spacing=self.ct.spacing)
            elif isinstance(target, ROIMask):
                mask = resampler3D.resampleImage3D(target, origin=self.ct.origin,
                                                gridSize=self.ct.gridSize,
                                                spacing=self.ct.spacing)
            else:
                raise Exception(target.__class__.__name__ + ' is not a supported class for roi')

            if targetMask is None:
                targetMask = mask
            else:
                targetMask.imageArray = np.logical_or(targetMask.imageArray, mask.imageArray)
            
            self.objectives.setTarget(target.name, mask, targetPrescription)

        if targetMask is None:
            raise Exception('No ROIContour nor ROIMask found in class attribut targets - User must specify')

        self.targetMask = targetMask

    def createBeams(self, plan):
        """
        Creates the beams of the plan

        Parameters
        ----------
        plan: RTPlan
            plan
        """
        for beam in plan:
            plan.removeBeam(beam)

        from opentps.core.data.plan import PlanIonBeam
        for i, gantryAngle in enumerate(self.gantryAngles):
            beam = PlanIonBeam()
            beam.gantryAngle = gantryAngle
            beam.couchAngle = self.couchAngles[i]
            beam.isocenterPosition = self.targetMask.centerOfMass
            beam.id = i
            if self.beamNames:
                beam.name = self.beamNames[i]
            else:
                beam.name = 'B' + str(i)
            if self.rangeShifters and self.rangeShifters[i]:
                beam.rangeShifter = self.rangeShifters[i]

            plan.appendBeam(beam)

    def initializeBeams(self, plan):
        """
        Initializes the beams of the plan

        Parameters
        ----------
        plan: RTPlan
            plan
        """
        initializer = PlanInitializer()
        initializer.ctCalibration = self.calibration
        initializer.ct = self.ct
        initializer.plan = plan
        initializer.targetMask = self.targetMask
        initializer.placeSpots(self.spotSpacing, self.layerSpacing, self.targetMargin, self.layersToSpacingAlignment,
                               self.proximalLayers, self.distalLayers)


    def setScoringParameters(self, scoringGridSize:Optional[Sequence[int]]=None, scoringSpacing:Optional[Sequence[float]]=None,
                                scoringOrigin:Optional[Sequence[int]]=None, adapt_gridSize_to_new_spacing=False):
        """
        Sets the scoring parameters

        Parameters
        ----------
        scoringGridSize: Sequence[int]
            scoring grid size
        scoringSpacing: Sequence[float]
            scoring spacing
        scoringOrigin: Sequence[float]
            scoring origin
        adapt_gridSize_to_new_spacing: bool
            If True, automatically adapt the gridSize to the new spacing
        """
        if adapt_gridSize_to_new_spacing and scoringGridSize is not None:
            raise ValueError('Cannot adapt gridSize to new spacing if scoringGridSize provided.')
        
        if scoringSpacing is not None: self.scoringVoxelSpacing = scoringSpacing
        if scoringGridSize is not None: self.scoringGridSize = scoringGridSize
        if scoringOrigin is not None: self.scoringOrigin = scoringOrigin
        
        if adapt_gridSize_to_new_spacing:
            self.scoringGridSize = np.floor(self.ct.gridSize*self.ct.spacing/self.scoringVoxelSpacing).astype(int)

        for objective in self.objectives.fidObjList:
            objective._updateMaskVec(spacing=self.scoringVoxelSpacing, gridSize=self.scoringGridSize, origin=self.scoringOrigin)
            
class Robustness:
    """
    This class is used to compute the robustness of a plan.

    Attributes
    ----------
    selectionStrategy : str
        The selection strategy used to select the scenarios.
        It can be "REDUCED_SET" or "ALL" or "DISABLED".
    setupSystematicError : list (default = [1.6, 1.6, 1.6]) (mm)
        The setup systematic error in mm.
    setupRandomError : list (default = [1.4, 1.4, 1.4]) (mm, sigma)
        The setup random error in mm.
    rangeSystematicError : float (default = 1.6) (%)
        The range systematic error in %.
    numScenarios : int
        The number of scenarios.
    scenarios : list
        The list of scenarios.
    """
    class Strategies(Enum):
        DEFAULT = "DISABLED"
        DISABLED = "DISABLED"
        ALL = "ALL"
        REDUCED_SET = "REDUCED_SET"
        RANDOM = "RANDOM"

    def __init__(self):
        self.selectionStrategy = self.Strategies.DEFAULT
        self.setupSystematicError = [1.6, 1.6, 1.6]  # mm
        self.setupRandomError = [1.4, 1.4, 1.4]  # mm
        self.rangeSystematicError = 1.6  # %
        self.numScenarios = 0
        self.scenarios = []