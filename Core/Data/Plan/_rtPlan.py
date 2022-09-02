
__all__ = ['RTPlan']


import copy
import logging
import unittest
from typing import Sequence

import numpy as np

from Core.Data.Plan._planStructure import PlanStructure
from Core.Data.Plan._planIonBeam import PlanIonBeam
from Core.Data.Plan._planIonLayer import PlanIonLayer
from Core.Data.Plan._planIonSpot import PlanIonSpot
from Core.Data._patientData import PatientData

logger = logging.getLogger(__name__)


class RTPlan(PatientData):
    def __init__(self, name="RTPlan"):
        super().__init__(name=name)

        self.deliveredProtons = None
        self._beams = []
        self._layers = []
        self._spots = []
        self._numberOfFractionsPlanned: int = 1

        self.seriesInstanceUID = ""
        self.SOPInstanceUID = ""
        self.modality = ""
        self.radiationType = ""
        self.scanMode = "MODULATED"
        self.treatmentMachineName = ""

        self.originalDicomDataset = []

        self.planDesign = PlanStructure()

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

    def appendLayerAccum(self, layer: PlanIonLayer):
        self._layers.append(layer)

    def appendSpotAccum(self, spot: PlanIonSpot):
        self._spots.append(spot)

    def removeLayer(self, layer: PlanIonLayer):
        self._layers.remove(layer)

    @property
    def spotMUs(self) -> np.ndarray:
        mu = np.array([])

        for beam in self._beams:
            mu = np.concatenate((mu, beam.spotMUs))

        return mu

    @spotMUs.setter
    def spotMUs(self, w: Sequence[float]):
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
        t = np.array(t)

        ind = 0
        for beam in self._beams:
            beam.spotTimings = t[ind:ind + len(beam.spotTimings)]
            ind += len(beam.spotTimings)

    @property
    def spotXY(self) -> np.ndarray:
        xy = np.array([])
        for beam in self._beams:
            beamXY = list(beam.spotXY)
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
        self._fusionDuplicates()
        for beam in self._beams:
            beam.simplify(threshold=threshold)

    def reorderPlan(self, order_layers="decreasing", order_spots="scanAlgo"):
        for beam in self._beams:
            beam.reorderLayers(order_layers)
            for layer in beam._layers:
                layer.reorderSpots(order_spots)

    def removeZeroMUSpots(self):
        for beam in self._beams:
            for layer in beam._layers:
                index_to_keep = np.flatnonzero(np.array(layer._mu) > 0.)
                layer._mu = np.array([layer._mu[i] for i in range(len(layer._mu)) if i in index_to_keep])
                layer._x = np.array([layer._x[i] for i in range(len(layer._x)) if i in index_to_keep])
                layer._y = np.array([layer._y[i] for i in range(len(layer._y)) if i in index_to_keep])

        # Remove empty layers
        for beam in self._beams:
            beam._layers = [layer for layer in beam._layers if len(layer._mu) > 0]

    def copy(self):
        return copy.deepcopy(self)  # recursive copy

    def _fusionDuplicates(self):
        # TODO
        raise NotImplementedError()

    def appendSpot(self, beam: PlanIonBeam, layer: PlanIonLayer, spot_index: int):
        """
        Assign a particular spot (beam, layer, spot_index) to plan
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
        t = None if len(layer._timings) == 0 else layer._timings[spot_index]
        self._beams[index_beam]._layers[index_layer].appendSpot(layer._x[spot_index], layer._y[spot_index],
                                                                layer._mu[spot_index], t)

    def appendLayer(self, beam: PlanIonBeam, layer: PlanIonLayer):
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
        plan = self.copy()
        plan._beams = []
        return plan


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

    def testLenWithTimings(self):
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

        np.testing.assert_array_equal(layer1.spotX, [3, 0, 1, 2])
        np.testing.assert_array_equal(layer1.spotY, [0, 1, 2, 2])
        np.testing.assert_array_equal(layer1.spotMUs, np.array([0.1, 0.2, 0.3, 0.5]))

        np.testing.assert_array_equal(layer0.spotX, [3, 0, 2, 1])
        np.testing.assert_array_equal(layer0.spotY, [0, 3, 3, 5])
        np.testing.assert_array_equal(layer0.spotMUs, np.array([0.1, 0.2, 0.5, 0.3]))


if __name__ == '__main__':
    unittest.main()
