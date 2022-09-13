__all__ = ['PlanDesign']

import logging

import numpy as np
import pydicom

from Core.Data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images._ctImage import CTImage
from Core.Data.Images._roiMask import ROIMask
from Core.Data.Plan import PlanIonBeam, _rangeShifter
from Core.Data.Plan._objectivesList import ObjectivesList
from Core.Data._patientData import PatientData
from Core.Processing.ImageProcessing import resampler3D
from Core.Processing.PlanOptimization.planInitializer import PlanInitializer

logger = logging.getLogger(__name__)


class PlanDesign(PatientData):
    def __init__(self):
        super().__init__()

        self.spotSpacing = 5.0
        self.layerSpacing = 5.0
        self.targetMargin = 5.0
        self.targetMask: ROIMask = None
        self.proximalLayers = 1
        self.distalLayers = 1
        self.layersToSpacingAlignment = False
        self.calibration: AbstractCTCalibration = None
        self.ct: CTImage = None
        self.beamNames = []
        self.gantryAngles = []
        self.couchAngles = []
        self.accumulatedLayer = 0
        self.accumulatedSpot = 0
        self.rangeShifters: _rangeShifter = []

        self.objectives = ObjectivesList()
        self.beamlets = []
        self.beamletsLET = []

        self.robustOpti = {"Strategy": "Disabled", "syst_setup": [0.0, 0.0, 0.0], "rand_setup": [0.0, 0.0, 0.0],
                           "syst_range": 0.0}
        self.scenarios = []
        self.numScenarios = 0

    def buildPlan(self):
        # Spot placement
        from Core.Data.Plan import RTPlan
        plan = RTPlan("NewPlan")
        plan.SOPInstanceUID = pydicom.uid.generate_uid()
        plan.seriesInstanceUID = plan.SOPInstanceUID + ".1"
        plan.modality = "Ion therapy"
        plan.radiationType = "Proton"
        plan.scanMode = "MODULATED"
        plan.treatmentMachineName = "Unknown"

        self.createBeams(plan)
        self.initializeBeams(plan)
        plan.planDesign = self
        for beam in plan.beams:
            beam.reorderLayers('decreasing')

        return plan

    def defineTargetMaskAndPrescription(self):
        from Core.Data._roiContour import ROIContour

        targetMask = None
        for objective in self.objectives.fidObjList:
            if objective.metric == objective.Metrics.DMIN:
                roi = objective.roi

                self.objectives.targetPrescription = objective.limitValue  # TODO: User should enter this value

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
        for beam in plan:
            plan.removeBeam(beam)

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
                beam.rangeShifter.ID = self.rangeShifters[i].ID
                beam.rangeShifter.type = self.rangeShifters[i].type

            plan.appendBeam(beam)

    def initializeBeams(self, plan):
        initializer = PlanInitializer()
        initializer.ctCalibration = self.calibration
        initializer.ct = self.ct
        initializer.plan = plan
        initializer.targetMask = self.targetMask
        initializer.placeSpots(self.spotSpacing, self.layerSpacing, self.targetMargin, self.layersToSpacingAlignment,
                               self.proximalLayers, self.distalLayers)
