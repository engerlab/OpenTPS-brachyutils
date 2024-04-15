
from __future__ import annotations

__all__ = ['RTPlan']


import copy
import logging
import unittest
from typing import Sequence
from opentps.core.data._patientData import PatientData

import numpy as np

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentps.core.data.plan._planIonBeam import PlanIonBeam
    from opentps.core.data.plan._planIonLayer import PlanIonLayer
    from opentps.core.data.plan._planIonSpot import PlanIonSpot

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
    deliveredProtons: float
        Number of protons delivered in the plan.
    beams: list of PlanIonBeam
        List of beams in the plan.
    layers: list of PlanIonLayer
        List of layers in the plan.
    spotMUs: np.ndarray
        Array of spot monitor units.
    spotTimings: np.ndarray
        Array of spot timings.
    spotIrradiationDurations: np.ndarray
        Array of spot irradiation durations.
    spotXY: np.ndarray
        Array of spot XY coordinates.
    meterset: float
        Total number of monitor units in the plan.
    beamCumulativeMetersetWeight: np.ndarray
        Array of beam cumulative meterset weights.
    layerCumulativeMetersetWeight: np.ndarray
        Array of layer cumulative meterset weights.
    meterset: float
        Total number of monitor units in the plan.
    numberOfSpots: int
        Number of spots in the plan.
    numberOffractionsPlanned: int (default: 1)
        Number of fractions planned.
    """
    def __init__(self, name="RTPlan", patient=None):
        self.deliveredProtons = None
        self._beams = []
        self._numberOfFractionsPlanned: int = 1

        self.seriesInstanceUID = ""
        self.SOPInstanceUID = ""
        self.modality = ""
        self.radiationType = ""
        self.scanMode = "MODULATED"
        self.treatmentMachineName = ""

        self.originalDicomDataset = []

        self.planDesign = None


        super().__init__(name=name, patient=patient)

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
    def layers(self) -> Sequence[PlanIonLayer]:
        layers = []
        for beam in self.beams:
            layers.extend(beam.layers)

        return layers

    @property
    def spotMUs(self) -> np.ndarray:
        mu = np.array([])

        for beam in self._beams:
            mu = np.concatenate((mu, beam.spotMUs))

        return mu

    @spotMUs.setter
    def spotMUs(self, w: Sequence[float]):
        if len(w) != self.numberOfSpots:
            raise ValueError(f'Cannot spotMU of size {len(w)} to size {self.numberOfSpots}')
        w = np.array(w)

        ind = 0
        for beam in self._beams:
            beam.spotMUs = w[ind:ind + len(beam.spotMUs)]
            ind += len(beam.spotMUs)

    @property
    def spotTimings(self) -> np.ndarray:
        timings = np.array([])

        for beam in self._beams:
            timings = np.concatenate((timings, beam.spotTimings))

        return timings

    @spotTimings.setter
    def spotTimings(self, t: Sequence[float]):
        if len(t) != self.numberOfSpots:
            raise ValueError(f'Cannot set spot timings of size {len(t)} to size {self.numberOfSpots}')
        t = np.array(t)

        ind = 0
        for beam in self._beams:
            beam.spotTimings = t[ind:ind + len(beam.spotTimings)]
            ind += len(beam.spotTimings)

    @property
    def spotIrradiationDurations(self) -> np.ndarray:
        durations = np.array([])

        for beam in self._beams:
            durations = np.concatenate((durations, beam.spotIrradiationDurations))

        return durations

    @spotIrradiationDurations.setter
    def spotIrradiationDurations(self, t: Sequence[float]):
        if len(t) != self.numberOfSpots:
            raise ValueError(f'Cannot set spot durations of size {len(t)} to size {self.numberOfSpots}')
        t = np.array(t)

        ind = 0
        for beam in self._beams:
            beam.spotIrradiationDurations = t[ind:ind + beam.numberOfSpots]
            ind += beam.numberOfSpots

    @property
    def spotXY(self) -> np.ndarray:
        xy = np.array([])
        for beam in self._beams:
            beamXY = beam.spotXY
            if len(beamXY) <= 0:
                continue

            if len(xy) <= 0:
                xy = beamXY
            else:
                xy = np.concatenate((xy, beamXY))

        return xy

    @property
    def meterset(self) -> float:
        return np.sum(np.array([beam.meterset for beam in self._beams]))

    @property
    def beamCumulativeMetersetWeight(self) -> np.ndarray:
        v_finalCumulativeMetersetWeight = np.array([])
        for beam in self._beams:
            cumulativeMetersetWeight = 0
            for layer in beam.layers:
                cumulativeMetersetWeight += sum(layer.spotWeights)
            v_finalCumulativeMetersetWeight = np.concatenate((v_finalCumulativeMetersetWeight, np.array([cumulativeMetersetWeight])))
        return v_finalCumulativeMetersetWeight

    @property
    def layerCumulativeMetersetWeight(self) -> np.ndarray:
        v_cumulativeMeterset = np.array([])
        for beam in self._beams:
            beamMeterset = 0
            for layer in beam.layers:
                beamMeterset += sum(layer.spotWeights)
                v_cumulativeMeterset = np.concatenate((v_cumulativeMeterset, np.array([beamMeterset])))
        return v_cumulativeMeterset

    @property
    def numberOfSpots(self) -> int:
        return np.sum(np.array([beam.numberOfSpots for beam in self._beams]))

    @property
    def numberOfFractionsPlanned(self) -> int:
        return self._numberOfFractionsPlanned

    @numberOfFractionsPlanned.setter
    def numberOfFractionsPlanned(self, fraction: int):
        if fraction != self._numberOfFractionsPlanned:
            self.spotMUs = self.spotMUs * (self._numberOfFractionsPlanned / fraction)
            self._numberOfFractionsPlanned = fraction

    def simplify(self, threshold: float = 0.0):
        """
        Simplify the plan by removing duplicate beams and simplifying each beam

        Parameters
        ----------
        threshold : float (default 0.0)
            The threshold to use for simplifying each beam
        """
        self._fusionDuplicates()
        for beam in self._beams:
            beam.simplify(threshold=threshold)
        
        # Remove empty beams
        self._beams = [beam for beam in self._beams if len(beam._layers) > 0]

    def reorderPlan(self, order_layers="decreasing", order_spots="scanAlgo"):
        """
        Reorder the plan by reordering each beam

        Parameters
        ----------
        order_layers: str or list of int (default: 'decreasing')
            order of the layers. If 'decreasing' or 'scanAlgo', the layers are ordered by decreasing nominal energy.
            If a list of int, the layers are ordered according to the list.
        order_spots: str or Sequence[int] (default: 'scanAlgo')
            the way the spots are sorted.
                If str, the following options are available:
                    - 'scanAlgo': the way scanAlgo sort spots in a serpentine fashion
                    - 'timing': sort according to the start time of the spots
                If Sequence[int], the spots a reordered according to the order of the indices
        """
        for beam in self._beams:
            beam.reorderLayers(order_layers)
            for layer in beam._layers:
                layer.reorderSpots(order_spots)

    def copy(self):
        return copy.deepcopy(self)  # recursive copy

    def _fusionDuplicates(self):
        if len(self) > 1:
            # if same gantry angle and couch angle
            unique_angles = [(self._beams[0].gantryAngle, self._beams[0].couchAngle)]
            ind = 1
            while ind < len(self._beams):
                current_angle = (self._beams[ind].gantryAngle, self._beams[ind].couchAngle)
                if current_angle in unique_angles:
                    #fusion
                    match_ind = unique_angles.index(current_angle) # find index in unique angle
                    if self._beams[ind].isocenterPosition != self._beams[match_ind].isocenterPosition:
                        print(f"Warning: Isocenter positions different in beams with same gantry and couch angles. Choosing the Isocenter position {self._beams[match_ind].isocenterPosition}")
                    if self._beams[ind].mcsquareIsocenter != self._beams[match_ind].mcsquareIsocenter:
                        print(f"Warning: MCsquare Isocenter positions different in beams with same gantry and couch angles. Choosing the Isocenter position {self._beams[match_ind].mcsquareIsocenter}")
                    if self._beams[ind].rangeShifter != self._beams[match_ind].rangeShifter:
                        print(f"Warning: Range shifter different in beams with same gantry and couch angles. Choosing Range shifter {self._beams[match_ind].rangeShifter}")
                                
                    self._beams[match_ind]._layers.extend(self._beams[ind]._layers) # merge layers
                    self.removeBeam(self._beams[ind])
                else:
                    unique_angles.append(current_angle)
                    ind += 1


    def appendSpot(self, beam: PlanIonBeam, layer: PlanIonLayer, spot_index: int):
        """
        Assign a particular spot (beam, layer, spot_index) to plan

        Parameters
        ----------
        beam: PlanIonBeam
            The beam of the spot to assign
        layer: PlanIonLayer
            The layer of the spot to assign
        spot_index: int
            The index of the spot to assign
        """
        # Integrate in RTPlan
        # List gantry angles in plan
        gantry_angles = [] if self._beams == [] else [b.gantryAngle for b in self._beams]
        if beam.gantryAngle not in gantry_angles:
            new_beam = beam.createEmptyBeamWithSameMetaData()
            self._beams.append(new_beam)
            gantry_angles.append(beam.gantryAngle)

        index_beam = np.where(np.array(gantry_angles) == beam.gantryAngle)[0][0]
        energies = [] if self._beams[index_beam]._layers == [] else [l.nominalEnergy for l in
                                                                     self._beams[index_beam]._layers]
        current_energy_index = np.flatnonzero(
            abs(np.array(energies) - layer.nominalEnergy) < 0.05)  # if delta energy < 0.05: same layer

        if current_energy_index.size == 0:  # layer.nominalEnergy not in energies:
            new_layer = layer.createEmptyLayerWithSameMetaData()
            self._beams[index_beam].appendLayer(new_layer)
            index_layer = -1
        else:
            index_layer = current_energy_index[0]
        t = None if len(layer._startTime) == 0 else layer._startTime[spot_index]
        d = None if len(layer._irradiationDuration) == 0 else layer._irradiationDuration[spot_index]
        self._beams[index_beam]._layers[index_layer].appendSpot(layer._x[spot_index], layer._y[spot_index],
                                                                layer._mu[spot_index], t, d)

    def appendLayer(self, beam: PlanIonBeam, layer: PlanIonLayer):
        """
        Assign a particular layer (beam, layer) to plan

        Parameters
        ----------
        beam: PlanIonBeam
            The beam of the layer to assign
        layer: PlanIonLayer
            The layer to assign
        """
        gantry_angles = [] if self._beams == [] else [b.gantryAngle for b in self._beams]
        if beam.gantryAngle not in gantry_angles:
            new_beam = beam.createEmptyBeamWithSameMetaData()
            self._beams.append(new_beam)
            gantry_angles.append(beam.gantryAngle)

        index_beam = np.where(np.array(gantry_angles) == beam.gantryAngle)[0][0]
        energies = [] if self._beams[index_beam]._layers == [] else [l.nominalEnergy for l in
                                                                     self._beams[index_beam]._layers]
        current_energy_index = np.flatnonzero(
            abs(np.array(energies) - layer.nominalEnergy) < 0.05)  # if delta energy < 0.05: same layer

        if current_energy_index.size > 0:
            raise ValueError('Layer already exists in plan')

        self._beams[index_beam].appendLayer(layer)
        self._layers.append(layer)

    def createEmptyPlanWithSameMetaData(self):
        """
        Create an empty plan with the same metadata as the current plan
        """
        plan = self.copy()
        plan._beams = []
        return plan


class PlanIonLayerTestCase(unittest.TestCase):
    def testLen(self):
        from opentps.core.data.plan import PlanIonBeam, PlanIonLayer

        plan = RTPlan()
        beam = PlanIonBeam()
        layer = PlanIonLayer(nominalEnergy=100.)
        layer.appendSpot(0, 0, 1)

        beam.appendLayer(layer)

        plan.appendBeam(beam)
        self.assertEqual(len(plan), 1)

        plan.removeBeam(beam)
        self.assertEqual(len(plan), 0)

    def testLenWithTimings(self):
        from opentps.core.data.plan import PlanIonBeam, PlanIonLayer

        plan = RTPlan()
        beam = PlanIonBeam()
        layer = PlanIonLayer(nominalEnergy=100.)
        layer.appendSpot(0, 0, 1, 0.5)

        beam.appendLayer(layer)

        plan.appendBeam(beam)
        self.assertEqual(len(plan), 1)

        plan.removeBeam(beam)
        self.assertEqual(len(plan), 0)

    def testReorderPlan(self):
        from opentps.core.data.plan import PlanIonBeam, PlanIonLayer

        plan = RTPlan()
        beam = PlanIonBeam()
        layer = PlanIonLayer(nominalEnergy=100.)
        x = [0, 2, 1, 3]
        y = [1, 2, 2, 0]
        mu = [0.2, 0.5, 0.3, 0.1]
        layer.appendSpot(x, y, mu)
        beam.appendLayer(layer)

        layer2 = PlanIonLayer(nominalEnergy=120.)
        x2 = [0, 2, 1, 3]
        y2 = [3, 3, 5, 0]
        mu2 = [0.2, 0.5, 0.3, 0.1]
        layer2.appendSpot(x2, y2, mu2)
        beam.appendLayer(layer2)

        plan.appendBeam(beam)
        plan.reorderPlan()

        layer0 = plan._beams[0]._layers[0]
        layer1 = plan._beams[0]._layers[1]
        self.assertEqual(layer0.nominalEnergy, 120.)
        self.assertEqual(layer1.nominalEnergy, 100.)

        np.testing.assert_array_equal(layer1.spotX, np.array([3, 0, 1, 2]))
        np.testing.assert_array_equal(layer1.spotY, np.array([0, 1, 2, 2]))
        np.testing.assert_array_almost_equal(layer1.spotMUs, np.array([0.1, 0.2, 0.3, 0.5]))

        np.testing.assert_array_equal(layer0.spotX, np.array([3, 0, 2, 1]))
        np.testing.assert_array_equal(layer0.spotY, np.array([0, 3, 3, 5]))
        np.testing.assert_array_almost_equal(layer0.spotMUs, np.array([0.1, 0.2, 0.5, 0.3]))

    def testFusionDuplicates(self):
        from opentps.core.data.plan import PlanIonBeam, PlanIonLayer

        plan = RTPlan()
        beam1 = PlanIonBeam()
        beam1.gantryAngle = 0
        beam1.couchAngle = 0
        layer = PlanIonLayer(nominalEnergy=100.)
        x = [0, 2, 1, 3]
        y = [1, 2, 2, 0]
        mu = [0.2, 0.5, 0.3, 0.1]
        layer.appendSpot(x, y, mu)
        beam1.appendLayer(layer)
        plan.appendBeam(beam1)

        beam2 = PlanIonBeam()
        beam2.gantryAngle = 90
        beam2.couchAngle = 45
        plan.appendBeam(beam2)
        beam3 = PlanIonBeam()
        beam3.gantryAngle = 0
        beam3.couchAngle = 0
        layer3 = PlanIonLayer(nominalEnergy=100.)
        x = [1, 3, 2, 4]
        y = [2, 3, 3, 1]
        mu = [0.3, 0.6, 0.4, 0.2]
        layer3.appendSpot(x, y, mu)
        beam3.appendLayer(layer3)
        plan.appendBeam(beam3)

        plan._fusionDuplicates()
        self.assertEqual(len(plan._beams),2)
        self.assertEqual(len(plan._beams[0]._layers),2)
        np.testing.assert_array_equal(plan._beams[0]._layers[0].spotX, np.array([0, 2, 1, 3]))
        np.testing.assert_array_equal(plan._beams[0]._layers[1].spotX, np.array([1, 3, 2, 4]))
        np.testing.assert_array_equal(plan._beams[0]._layers[0].spotY, np.array([1, 2, 2, 0]))
        np.testing.assert_array_equal(plan._beams[0]._layers[1].spotY, np.array([2, 3, 3, 1]))
        np.testing.assert_array_almost_equal(plan._beams[0]._layers[0].spotMUs, np.array([0.2, 0.5, 0.3, 0.1]))
        np.testing.assert_array_almost_equal(plan._beams[0]._layers[1].spotMUs, np.array([0.3, 0.6, 0.4, 0.2]))

    def testSimplify(self):
        from opentps.core.data.plan import PlanIonBeam, PlanIonLayer

        plan = RTPlan()
        beam1 = PlanIonBeam()
        beam1.gantryAngle = 0
        beam1.couchAngle = 0
        layer = PlanIonLayer(nominalEnergy=100.)
        x = [0, 2, 1, 3]
        y = [1, 2, 2, 0]
        mu = [0.2, 0.5, 0.3, 0.1]
        layer.appendSpot(x, y, mu)
        beam1.appendLayer(layer)
        plan.appendBeam(beam1)

        beam2 = PlanIonBeam()
        beam2.gantryAngle = 90
        beam2.couchAngle = 45
        plan.appendBeam(beam2) #empty beam
        beam3 = PlanIonBeam()
        beam3.gantryAngle = 0
        beam3.couchAngle = 0
        layer3 = PlanIonLayer(nominalEnergy=99.97)
        x = [1, 3, 2, 3, 10]
        y = [2, 3, 3, 0, 10]
        mu = [0.3, 0.6, 0.4, 0.2, 0.]
        layer3.appendSpot(x, y, mu)
        beam3.appendLayer(layer3)
        plan.appendBeam(beam3)

        plan.simplify()
        self.assertEqual(len(plan._beams),1)
        self.assertEqual(len(plan._beams[0]._layers),1)
        np.testing.assert_array_equal(plan._beams[0]._layers[0].spotX, np.array([0, 2, 1, 3, 3, 2]))
        np.testing.assert_array_equal(plan._beams[0]._layers[0].spotY, np.array([1, 2, 2, 0, 3, 3]))
        np.testing.assert_array_almost_equal(plan._beams[0]._layers[0].spotMUs, np.array([0.2, 0.5, 0.6, 0.3, 0.6, 0.4]))


if __name__ == '__main__':
    unittest.main()
