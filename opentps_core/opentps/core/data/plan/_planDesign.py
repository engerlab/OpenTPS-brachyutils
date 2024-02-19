
__all__ = ['PlanDesign']

import logging
import time
from typing import Optional, Sequence, Union

import numpy as np
import pydicom

from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.plan._rangeShifter import RangeShifter
from opentps.core.processing.imageProcessing import resampler3D
from opentps.core.data._patientData import PatientData
from opentps.core.data.plan._objectivesList import ObjectivesList
from opentps.core.processing.planEvaluation.robustnessEvaluation import Robustness
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
        mask of the target
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
        self.targetMask: ROIMask = None
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
        self._gridSize = gridSize

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

    def defineTargetMaskAndPrescription(self):
        """
        Defines the target mask and the prescription
        """
        from opentps.core.data._roiContour import ROIContour

        targetMask = None
        for objective in self.objectives.fidObjList:
            if objective.metric == objective.Metrics.DMIN:
                roi = objective.roi

                self.objectives.setTarget(objective.roiName, objective.limitValue)

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

        if targetMask is None:
            raise Exception('Could not find a target volume in dose fidelity objectives')

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
            
