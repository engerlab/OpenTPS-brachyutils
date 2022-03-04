import copy

from scipy.ndimage import morphology

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Images.rspImage import RSPImage
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.rtPlan import RTPlan


class PlanOptimizer:
    def __init__(self):
        self.calibration:AbstractCTCalibration=None
        self.ct:CTImage=None
        self.plan:RTPlan=None
        self.targetMask:ROIMask=None
        self._objectiveTerms = []

    def intializePlan(self, spotSpacing:float, layerSpacing:float, targetMargin:float=0., ):
        #TODO Range shifter

        self._roiDilated = copy.deepcopy(self.targetMask)
        self._roiDilated.dilate(targetMargin)

        rspImage = RSPImage.fromCT(self.ct, self.calibration, energy=100.)

        for beam in self.plan:
            beam.isocenterPosition = self._roiDilated.centerOfMass

            cumRSP = rspImage.computeCumulativeWEPL(beam)

    def run(self):
        pass