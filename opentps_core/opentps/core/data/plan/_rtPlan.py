from __future__ import annotations

__all__ = ['RTPlan']

import logging
import numpy as np
from typing import TYPE_CHECKING, Union, Sequence
from opentps.core.data._patientData import PatientData

if TYPE_CHECKING:
    from opentps.core.data.plan._planProtonBeam import PlanProtonBeam
    from opentps.core.data.plan._planPhotonBeam import PlanPhotonBeam
    from opentps.core.data.plan._protonPlan import ProtonPlan
    from opentps.core.data.plan._photonPlan import PhotonPlan   

logger = logging.getLogger(__name__)


class RTPlan(PatientData):
    """
    Class for storing the data of a single RTPlan. Inherits from PatientData.

    Attributes
    ----------
    name: str (default: "RTPlan")
        Name of the RTPlan.

    patient: Patient
        Patient object to which the RTPlan belongs.

    beams: list of PlanIonBeam or PlanPhotonBeam
        List of beams in the plan.

    numberOffractionsPlanned: int (default: 1)
        Number of fractions planned.
    """

    def __init__(self, name="RTPlan", patient=None):
        self._beams = []
        self._numberOfFractionsPlanned: int = 1

        self.seriesInstanceUID = ""
        self.sopInstanceUID = ""
        self.modality = ""
        self.radiationType = ""
        self.scanMode = "MODULATED"
        self.treatmentMachineName = ""
        self.rangeShifter = []        
        self.rtPlanName = ""

        self.originalDicomDataset = []

        self.planDesign = None
        self.SAD_mm = 1000


        super().__init__(name=name, patient=patient)

    def __getitem__(self, beamNb) -> PlanProtonBeam:
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
    def beams(self) -> Sequence[Union[PlanProtonBeam, PlanPhotonBeam]]:
        # For backwards compatibility but we can now access each beam with indexing brackets
        return [beam for beam in self._beams]

    def appendBeam(self, beam: Union[PlanProtonBeam, PlanPhotonBeam]):
        self._beams.append(beam)

    def removeBeam(self, beam: Union[PlanProtonBeam, PlanPhotonBeam]):
        self._beams.remove(beam)

    @property
    def numberOfFractionsPlanned(self) -> int:
        return self._numberOfFractionsPlanned

    @numberOfFractionsPlanned.setter
    def numberOfFractionsPlanned(self, fraction: int):
        if fraction != self._numberOfFractionsPlanned:
            self.spotMUs = self.spotMUs * (self._numberOfFractionsPlanned / fraction)
            self._numberOfFractionsPlanned = fraction

    @staticmethod
    def createPlan(radiationType):
        if radiationType.upper() == "PHOTON":
            return PhotonPlan()
        elif radiationType.upper() == "ION":
            return ProtonPlan()
        else:
            return RTPlan(radiationType)
