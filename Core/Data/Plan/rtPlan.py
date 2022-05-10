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
    def __init__(self, name="RTPlan", patientInfo=None):
        super().__init__(name=name, patientInfo=patientInfo)

        self._beams = []
        self._numberOfFractionsPlanned:int = 1

        self.seriesInstanceUID = ""
        self.SOPInstanceUID = ""
        # self.PatientInfo = {}
        # self.StudyInfo = {}
        # self.DcmFile = ""
        self.modality = ""
        self.radiationType = ""
        self.scanMode = ""
        self.treatmentMachineName = ""
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
    def spotTimings(self) -> np.ndarray:
        timings = np.array([])

        for beam in self._beams:
            timings = np.concatenate((timings, beam.spotTimings))

        return timings

    @spotTimings.setter
    def spotTimings(self, t:Sequence[float]):
        t = np.array(t)

        ind = 0
        for beam in self._beams:
            beam.spotTimings = t[ind:ind+len(beam.spotTimings)]
            ind += len(beam.spotTimings)

    @property
    def meterset(self) -> float:
        return np.sum(np.array([beam.meterset for beam in self._beams]))

    @property
    def numberOfSpots(self) -> int:
        return np.sum(np.array([beam.numberOfSpots for beam in self._beams]))

    @property
    def numberOfFractionsPlanned(self) -> int:
        return self._numberOfFractionsPlanned

    @numberOfFractionsPlanned.setter
    def numberOfFractionsPlanned(self, fraction: int):
        if fraction != self._numberOfFractionsPlanned:
            self.spotWeights = self.spotWeights * (self._numberOfFractionsPlanned / fraction)
            self._numberOfFractionsPlanned = fraction

    def simplify(self, threshold:float=0.0):
        self._fusionDuplicates()
        for beam in self._beams:
            beam.simplify(threshold=threshold)

    def reorderPlan(self, order_layers="decreasing", order_spots="scanAlgo"):
        for beam in self._beams:
            beam.reorderLayers(order_layers)
            for layer in beam._layers:
                layer.reorderSpots(order_spots)

    def removeZeroWeightSpots(self):
        for beam in self._beams:
            for layer in beam._layers:
                index_to_keep = np.flatnonzero(np.array(layer._weights)>0.)
                layer._weights = np.array([layer._weights[i] for i in range(len(layer._weights)) if i in index_to_keep])
                layer._x = np.array([layer._x[i] for i in range(len(layer._x)) if i in index_to_keep])
                layer._y = np.array([layer._y[i] for i in range(len(layer._y)) if i in index_to_keep])

        # Remove empty layers
        for beam in self._beams:
            beam._layers = [layer for layer in beam._layers if len(layer._weights)>0]

    
    def copy(self):
        return copy.deepcopy(self) # recursive copy


    def _fusionDuplicates(self):
        #TODO
        raise NotImplementedError()


    def appendSpot(self, beam:PlanIonBeam, layer:PlanIonLayer, spot_index:int):
        """
        Assign a particular spot (beam, layer, spot_index) to plan
        """
        # Integrate in RTPlan
        # List gantry angles in plan
        gantry_angles = [] if self._beams==[] else [b.gantryAngle for b in self._beams]
        if beam.gantryAngle not in gantry_angles:
            new_beam = beam.createEmptyBeamWithSameMetaData()
            self._beams.append(new_beam)
            gantry_angles.append(beam.gantryAngle)
        
        index_beam = np.where(np.array(gantry_angles)==beam.gantryAngle)[0][0]
        energies = [] if self._beams[index_beam]._layers==[] else [l.nominalEnergy for l in self._beams[index_beam]._layers]
        current_energy_index = np.flatnonzero(abs(np.array(energies) - layer.nominalEnergy) < 0.05) # if delta energy < 0.05: same layer

        if current_energy_index.size==0:#layer.nominalEnergy not in energies:
            new_layer = layer.createEmptyLayerWithSameMetaData()
            self._beams[index_beam].appendLayer(new_layer)
            index_layer = -1
        else:
            index_layer = current_energy_index[0]
        t = None if len(layer._timings)==0 else layer._timings[spot_index]
        self._beams[index_beam]._layers[index_layer].appendSpot(layer._x[spot_index], layer._y[spot_index], layer._weights[spot_index], t)


    def appendLayer(self, beam:PlanIonBeam, layer:PlanIonLayer):
        gantry_angles = [] if self._beams==[] else [b.gantryAngle for b in self._beams]
        if beam.gantryAngle not in gantry_angles:
            new_beam = beam.createEmptyBeamWithSameMetaData()
            self._beams.append(new_beam)
            gantry_angles.append(beam.gantryAngle)
        
        index_beam = np.where(np.array(gantry_angles)==beam.gantryAngle)[0][0]
        energies = [] if self._beams[index_beam]._layers==[] else [l.nominalEnergy for l in self._beams[index_beam]._layers]
        current_energy_index = np.flatnonzero(abs(np.array(energies) - layer.nominalEnergy) < 0.05) # if delta energy < 0.05: same layer

        if current_energy_index.size>0:
            raise ValueError('Layer already exists in plan')

        self._beams[index_beam].appendLayer(layer)


    def createEmptyPlanWithSameMetaData(self):
        plan = self.copy()
        plan._beams = []
        plan.beamlets = []
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
        weight = [0.2, 0.5, 0.3, 0.1]
        layer.appendSpot(x, y, weight)
        beam.appendLayer(layer)

        layer2 = PlanIonLayer(nominalEnergy=120.)
        x2 = [0, 2, 1, 3]
        y2 = [3, 3, 5, 0]
        weight2 = [0.2, 0.5, 0.3, 0.1]
        layer2.appendSpot(x2, y2, weight2)
        beam.appendLayer(layer2)

        plan.appendBeam(beam)
        plan.reorderPlan()

        layer0 = plan._beams[0]._layers[0]
        layer1 = plan._beams[0]._layers[1]
        self.assertEqual(layer0.nominalEnergy,120.)
        self.assertEqual(layer1.nominalEnergy,100.)

        np.testing.assert_array_equal(layer1.spotX, [3,0,1,2])
        np.testing.assert_array_equal(layer1.spotY, [0,1,2,2])
        np.testing.assert_array_equal(layer1.spotWeights, np.array([0.1,0.2,0.3,0.5]))

        np.testing.assert_array_equal(layer0.spotX, [3,0,2,1])
        np.testing.assert_array_equal(layer0.spotY, [0,3,3,5])
        np.testing.assert_array_equal(layer0.spotWeights, np.array([0.1,0.2,0.5,0.3]))







if __name__ == '__main__':
    unittest.main()