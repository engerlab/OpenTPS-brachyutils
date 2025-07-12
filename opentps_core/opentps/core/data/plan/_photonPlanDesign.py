
__all__ = ['PhotonPlanDesign']

import logging
import time
from typing import Sequence, Union

import numpy as np
import pydicom

from opentps.core.data.plan import PhotonPlan
from opentps.core.data.plan._robustnessPhoton import RobustnessPhoton
from opentps.core.data.plan._rtPlanDesign import RTPlanDesign
from opentps.core.processing.planEvaluation.robustnessEvaluation import RobustnessEvalPhoton
from opentps.core.processing.planOptimization.planInitializer_Photons import PhotonPlanInitializer

logger = logging.getLogger(__name__)


class PhotonPlanDesign(RTPlanDesign):
    """
    This class is used to store the plan design. It inherits from PatientData.

    Attributes
    ----------

    """
    def __init__(self):
        super().__init__()

        self.xBeamletSpacing_mm = 1.0
        self.yBeamletSpacing_mm = 1.0
        # self.robustOptimizationStrategy = None

        self.isocenterPosition_mm = None
        self.ROI_cropping = True

        self.robustness = RobustnessPhoton()
        self.robustnessEval = RobustnessEvalPhoton()

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
        if self._scoringVoxelSpacing is not None:
            return np.floor(self.ct.gridSize*self.ct.spacing/self.scoringVoxelSpacing).astype(int)
        else:
            return self.ct.gridSize

    def buildPlan(self):
        """
        Builds a plan from the plan design

        Returns
        --------
        PhotonPlan
            plan
        """
        start = time.time()
        plan = PhotonPlan("NewPlan")   
        plan.SOPInstanceUID = pydicom.uid.generate_uid()
        plan.seriesInstanceUID = plan.SOPInstanceUID + ".1"
        plan.modality = "RT Plan IOD"
        plan.radiationType = "Photon"
        plan.scanMode = "MODULATED"
        plan.treatmentMachineName = "Unknown"
        if self.isocenterPosition_mm is None:
            self.isocenterPosition_mm = self.targetMask.centerOfMass
            
        logger.info('Building plan ...')
        self.createBeams(plan)
        self.initializeBeams(plan)
        plan.planDesign = self

        logger.info("New photon plan created in {} sec".format(time.time() - start))
        logger.info("Number of beamlets: {}".format(plan.numberOfBeamlets))

        return plan

    def createBeams(self, plan):
        """
        Creates the beams of the plan

        Parameters
        ----------
        plan: PhotonPlan
            plan
        """
        for beam in plan:
            plan.removeBeam(beam)

        from opentps.core.data.plan import PlanPhotonBeam
        for i, gantryAngle in enumerate(self.gantryAngles):
            beam = PlanPhotonBeam()
            beam.gantryAngle_degree = gantryAngle
            beam.couchAngle_degree = self.couchAngles[i]
            beam.isocenterPosition_mm = self.isocenterPosition_mm 
            beam.id = i
            beam.xBeamletSpacing_mm = self.xBeamletSpacing_mm
            beam.yBeamletSpacing_mm = self.yBeamletSpacing_mm
            if self.beamNames:
                beam.name = self.beamNames[i]
            else:
                beam.name = 'B' + str(i)

            plan.appendBeam(beam)

    def initializeBeams(self, plan):
        """
        Initializes the beams of the plan

        Parameters
        ----------
        plan: RTPlan
            plan
        """
        initializer = PhotonPlanInitializer()
        initializer.ctCalibration = self.calibration
        initializer.ct = self.ct
        initializer.plan = plan
        initializer.targetMask = self.targetMask
        initializer.placeBeamlets(self.targetMargin)