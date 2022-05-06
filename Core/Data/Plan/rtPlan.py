import copy
import logging
import unittest
from typing import Sequence

import numpy as np

from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.patientData import PatientData

logger = logging.getLogger(__name__)


class RTPlan(PatientData):
    def __init__(self, patientInfo=None):
        super().__init__(patientInfo=patientInfo)

        self._beams = []
        self.numberOfFractionsPlanned:int = 1
        self.name = 'RTPlan'

        self.seriesInstanceUID = ""
        self.SOPInstanceUID = ""
        # self.PatientInfo = {}
        # self.StudyInfo = {}
        # self.DcmFile = ""
        self.modality = ""
        self.radiationType = ""
        self.scanMode = ""
        self.treatmentMachineName = ""
        self.name = ""
        # self.Objectives = OptimizationObjectives()
        # self.isLoaded = 0
        self.beamlets = []
        # self.OriginalDicomDataset = []
        # self.RobustOpti = {"Strategy": "Disabled", "syst_setup": [0.0, 0.0, 0.0], "rand_setup": [0.0, 0.0, 0.0], "syst_range": 0.0}
        self.scenarios = []
        self.numScenarios = 0


    def __getitem__(self, beamNb) -> PlanIonBeam:
        return self._beams[beamNb]

    def __len__(self):
        return len(self._beams)

    def __str__(self):
        s = ''
        for beam in self._beams:
            s += 'Beam\n'
            s += str(beam)
        return s

    @property
    def beams(self) -> Sequence[PlanIonBeam]:
        # For backwards compatibility but we can now access each beam with indexing brackets
        return [beam for beam in self._beams]

    def appendBeam(self, beam: PlanIonBeam):
        self._beams.append(beam)

    def removeBeam(self, beam: PlanIonBeam):
        self._beams.remove(beam)

    @property
    def spotWeights(self) -> np.ndarray:
        weights = np.array([])

        for beam in self._beams:
            weights = np.concatenate((weights, beam.spotWeights))

        return weights

    @spotWeights.setter
    def spotWeights(self, w:Sequence[float]):
        w = np.array(w)

        ind = 0
        for beam in self._beams:
            beam.spotWeights = w[ind:ind+len(beam.spotWeights)]
            ind += len(beam.spotWeights)

    @property
    def meterset(self) -> float:
        return np.sum(np.array([beam.meterset for beam in self._beams]))

    @property
    def numberOfSpots(self) -> int:
        return np.sum(np.array([beam.numberOfSpots for beam in self._beams]))

    def simplify(self, threshold:float=0.0):
        self._fusionDuplicates()
        for beam in self._beams:
            beam.simplify(threshold=threshold)

    def _fusionDuplicates(self):
        #TODO
        raise NotImplementedError()


class PlanIonLayerTestCase(unittest.TestCase):
    def testLen(self):
        plan = RTPlan()
        beam = PlanIonBeam()
        layer = PlanIonLayer(nominalEnergy=100.)
        layer.appendSpot(0, 0, 1)

        beam.appendLayer(layer)

        plan.appendBeam(beam)
        self.assertEqual(len(plan), 1)

        plan.removeBeam(beam)
        self.assertEqual(len(plan), 0)
