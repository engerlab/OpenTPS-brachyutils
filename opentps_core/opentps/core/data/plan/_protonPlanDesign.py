
__all__ = ['ProtonPlanDesign']

import logging
import time
from typing import  Sequence

import numpy as np

from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.plan._rangeShifter import RangeShifter
from opentps.core.data.plan._robustnessProton import RobustnessProton
from opentps.core.processing.planEvaluation.robustnessEvaluation import RobustnessEvalProton
from opentps.core.processing.planOptimization.planInitializer import PlanInitializer
from opentps.core.data.plan._rtPlanDesign import RTPlanDesign

logger = logging.getLogger(__name__)


class ProtonPlanDesign(RTPlanDesign):
    """
    This class is used to store the plan design. It inherits from PatientData.

    Attributes
    ----------
    spotSpacing: float (default: 5.0)
        spacing between spots in mm
    layerSpacing: float (default: 5.0)
        spacing between layers in mm
    scoringVoxelSpacing: float or list of float
        spacing of the scoring grid in mm
    proximalLayers: int (default: 1)
        number of proximal layers
    distalLayers: int (default: 1)
        number of distal layers
    layersToSpacingAlignment: bool (default: False)
        if True, the spacing between layers is aligned with the scoring grid
    rangeShifters: list of RangeShifter
        list of range shifters
    beamletsLET: list of Beamlet
        list of beamlets with LET
    """
    def __init__(self):
        super().__init__()

        self.spotSpacing = 5.0
        self.layerSpacing = 5.0
        self.proximalLayers = 1
        self.distalLayers = 1
        self.layersToSpacingAlignment = False
        self.rangeShifters: Sequence[RangeShifter] = []
        self.isocenterPosition_mm = None

        self.beamletsLET = []

        self.robustness = RobustnessProton()
        self.robustnessEval = RobustnessEvalProton()



    def buildPlan(self):
        """
        Builds a plan from the plan design

        Returns
        --------
        ProtonPlan
            plan
        """
        start = time.time()
        # Spot placement
        from opentps.core.data.plan import ProtonPlan
        plan = ProtonPlan("NewPlan")
        plan.seriesInstanceUID = "1.2.840.10008.5.1.4.1.1.481.8"
        plan.modality = "RT Ion Plan IOD"
        plan.radiationType = "PROTON"
        plan.scanMode = "MODULATED"
        plan.treatmentMachineName = "Unknown"
        if self.isocenterPosition_mm is None:
            self.isocenterPosition_mm = self.targetMask.centerOfMass
        logger.info('Building plan ...')
        self.createBeams(plan)
        self.initializeBeams(plan)
        plan.planDesign = self
        for beam in plan.beams:
            beam.reorderLayers('decreasing')

        logger.info("New proton plan created in {} sec".format(time.time() - start))
        logger.info("Number of spots: {}".format(plan.numberOfSpots))

        return plan

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

        from opentps.core.data.plan import PlanProtonBeam
        for i, gantryAngle in enumerate(self.gantryAngles):
            beam = PlanProtonBeam()
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


