import logging

import numpy as np

from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.patientData import PatientData

logger = logging.getLogger(__name__)


class RTPlan(PatientData):
    def __init__(self, patientInfo=None):
        super().__init__(patientInfo=patientInfo)

        self._beams = []

    def __getitem__(self, beamNb):
        return self._beams[beamNb]

    def __len__(self):
        return len(self._beams)

    def __str__(self):
        s = ''
        for beam in self._beams:
            s += 'Beam\n'
            s += str(beam)
        return s

    def appendBeam(self, beam: PlanIonBeam):
        self._beams.append(beam)

    def removeBeam(self, beam: PlanIonBeam):
        self._beams.remove(beam)

    @property
    def meterset(self) -> int:
        return np.sum(np.array([beam.meterset for beam in self._beams]))

    def simplify(self, threshold:float=0.0):
        self._fusionDuplicates()
        for beam in self._beams:
            beam.simplify(threshold=threshold)

    def _fusionDuplicates(self):
        #TODO
        raise NotImplementedError()
