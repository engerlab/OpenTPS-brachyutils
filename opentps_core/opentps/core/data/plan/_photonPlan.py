import logging

from opentps.core.data.plan._rtPlan import RTPlan
import numpy as np
from opentps.core.data.plan._planPhotonBeam import PlanPhotonBeam
from typing import Sequence
from opentps.core.data.plan._planPhotonSegment import PlanPhotonSegment
import copy

__all__ = ['PhotonPlan']
logger = logging.getLogger(__name__)

class PhotonPlan(RTPlan):
    """
            Class for storing the data of a single PhotonPlan. Inherits from RTPlan.

            Attributes
            ----------

    """
    def __init__(self, name="PhotonPlan", patient=None):
        super().__init__(name=name, patient=patient)
        self.sopInstanceUID = "1.2.840.10008.5.1.4.1.1.481.5"
        self.radiationType = "PHOTON"
        self.modality = "RT Plan IOD"
    
    @property
    def numberOfBeamlets(self) -> int:
        return np.sum([beam.numberOfBeamlets for beam in self._beams])
    
    @property
    def numberOfSegments(self):
        return np.sum([len(beam) for beam in self._beams])
    
    @property
    def beamletsAngle_rad(self):
        angles = []
        for segment in self.beamSegments:
            angles.extend([segment.gantryAngle_degree / 180 * np.pi] * len(segment))  
        return angles 

    def removeBeam(self, beam: PlanPhotonBeam):
        if isinstance(beam, Sequence):
            beams = beam
            for beam in beams:
                self.removeBeam(beam)
            return
        self._beams.remove(beam)

    @property
    def beamSegments(self) -> Sequence[PlanPhotonSegment]:
        segments = []
        for beam in self._beams:
            segments.extend(beam.beamSegments)
        return segments
    
    @property
    def beamlets(self) -> Sequence[PlanPhotonSegment]:
        beamlets = []
        for segment in self.beamSegments:
            beamlets.extend(segment.beamlets)
        return beamlets
    
    def createBeamletsFromSegments(self):
        for i,beam in enumerate(self._beams):
            print('Creating beamlets for beams for beam {}.'.format(i))
            beam.createBeamletsFromSegments()
     
    @property
    def beamletMUs(self) -> np.ndarray:
        mu = np.array([])

        for beam in self._beams:
            mu = np.concatenate((mu, beam.beamletMUs))

        return mu

    @beamletMUs.setter
    def beamletMUs(self, w: Sequence[float]):
        if len(w) != self.numberOfBeamlets:
            raise ValueError(f'Cannot spotMU of size {len(w)} to size {self.numberOfBeamlets}')
        w = np.array(w)

        ind = 0
        for beam in self._beams:
            beam.beamletMUs = w[ind:ind + len(beam.beamletMUs)]
            ind += len(beam.beamletMUs)

    @property
    def xBeamletSpacing_mm(self):
        return self._beams[0].xBeamletSpacing_mm
    
    @xBeamletSpacing_mm.setter
    def xBeamletSpacing(self, xSpacing):
        for beam in self._beams:
            beam.setXBeamletSpacing_mm(xSpacing)

    @property
    def yBeamletSpacing_mm(self):
        return self._beams[0].yBeamletSpacing_mm
    
    @yBeamletSpacing_mm.setter
    def yBeamletSpacing(self, ySpacing):
        for beam in self._beams:
            beam.setXBeamletSpacing_mm(ySpacing)

    @property
    def beamletsXY(self) -> np.ndarray:
        xy = np.array([])
        for beam in self._beams:
            beamXY = list(beam.beamletsXY)
            if len(beamXY) <= 0:
                continue

            if len(xy) <= 0:
                xy = beamXY
            else:
                xy = np.concatenate((xy, beamXY))
        return xy

    @property
    def cumulativeMeterset(self) -> float:
        return np.sum(np.array([beam.meterset for beam in self._beams]))

    @property
    def beamCumulativeMetersetWeight(self) -> np.ndarray:
        v_finalCumulativeMetersetWeight = np.array([])  
        for beam in self._beams:
            cumulativeMetersetWeight = 0
            for segment in beam.beamSegments:
                cumulativeMetersetWeight += sum(segment.beamletWeights)
            v_finalCumulativeMetersetWeight = np.concatenate((v_finalCumulativeMetersetWeight, np.array([cumulativeMetersetWeight])))
        return v_finalCumulativeMetersetWeight

    @property
    def beamSegmentCumulativeMetersetWeight(self) -> np.ndarray:
        v_cumulativeMeterset = np.array([])
        for beam in self._beams:
            beamMeterset = 0
            for layer in beam.beamSegments:
                beamMeterset += sum(layer.beamletWeights)
                v_cumulativeMeterset = np.concatenate((v_cumulativeMeterset, np.array([beamMeterset])))
        return v_cumulativeMeterset

    @property
    def numberOfFractionsPlanned(self) -> int:
        return self._numberOfFractionsPlanned

    @numberOfFractionsPlanned.setter
    def numberOfFractionsPlanned(self, fraction: int):
        if fraction != self._numberOfFractionsPlanned:
            self.beamletMUs = self.beamletMUs * (self._numberOfFractionsPlanned / fraction)
            self._numberOfFractionsPlanned = fraction

    def simplify(self, threshold: float = 0.0, gantryAngleTolerance: float = 0.01):
        print('Simplifying plan...')
        for beam in self._beams:
            beam.simplify(threshold = threshold, gantryAngleTolerance = gantryAngleTolerance)
        # Remove empty beams
        self._beams = [beam for beam in self._beams if len(beam) > 0]


    def copy(self):
        return copy.deepcopy(self)  # recursive copy

    def createEmptyPlanWithSameMetaData(self):
        plan = self.copy()
        plan._beams = []
        return plan