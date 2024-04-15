from __future__ import annotations

__all__ = ['PlanIonBeam']


import copy
from typing import Optional, Sequence, Union
import unittest

import numpy as np

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentps.core.data.plan._planIonLayer import PlanIonLayer
    from opentps.core.data.plan._rangeShifter import RangeShifter



class PlanIonBeam:
    """
    This class is used to store the information of an ion beam.

    Attributes
    ----------
    layers: list of PlanIonLayer
        list of layers
    name: str
        name of the beam
    isocenterPosition: list of float (default: [0, 0, 0])
        isocenter position of the beam
    mcsquareIsocenter: list of float (default: [0, 0, 0])
        isocenter position of the beam for MCSquare
    gantryAngle: float (default: 0.0)
        gantry angle of the beam
    couchAngle: float (default: 0.0)
        couch angle of the beam
    id: int (default: 0)
        id of the beam
    rangeShifter: RangeShifter (optional)
        range shifter of the beam
    seriesInstanceUID: str
        series instance UID of the beam
    spotMUs: list of float
        list of spot MUs
    spotIrradiationTimes: list of float
        list of spot irradiation times
    spotXY: np.ndarray
        array of spot XY positions
    spotTimes: np.ndarray
        array of spot times
    numberSpots: int
        number of spots
    meterset: float
        meterset of the beam
    """
    def __init__(self):
        self._layers:Sequence[PlanIonLayer] = []

        self.name = ""
        self.isocenterPosition = [0, 0, 0]
        self.mcsquareIsocenter = [0, 0, 0]
        self.gantryAngle = 0.0
        self.couchAngle = 0.0
        self.id = 0
        self.rangeShifter: Optional[RangeShifter] = None
        self.seriesInstanceUID = ""
        self.approxSpotsPeakPosList = None

    def __getitem__(self, layerNb) -> PlanIonLayer:
        """
        Get the layer at the given index.

        Parameters
        ----------
        layerNb: int
            index of the layer

        Returns
        ----------
        layer: PlanIonLayer
            layer at the given index
        """
        return self._layers[layerNb]

    def __len__(self):
        """
        Get the number of layers.

        Returns
        ----------
        nbLayers: int
            number of layers
        """
        return len(self._layers)

    def __str__(self):
        """
        Get the string representation of the layers.

        Returns
        ----------
        s: str
            string representation of the layers
        """
        s = ''
        for layer in self._layers:
            s += 'Layer\n'
            s += str(layer)

        return s

    @property
    def layers(self) -> Sequence[PlanIonLayer]:
        # For backwards compatibility but we can now access each layer with indexing brackets
        return [layer for layer in self._layers]

    def appendLayer(self, layer: PlanIonLayer):
        """
        Append a layer to the list of layers.

        Parameters
        ----------
        layer: PlanIonLayer
            layer to append
        """
        self._layers.append(layer)

    def removeLayer(self, layer: Union[PlanIonLayer, Sequence[PlanIonLayer]]):
        """
        Remove a layer from the list of layers.

        Parameters
        ----------
        layer: PlanIonLayer or list of PlanIonLayer
            layer to remove
        """
        if isinstance(layer, Sequence):
            layers = layer
            for layer in layers:
                self.removeLayer(layer)
            return

        self._layers.remove(layer)

    @property
    def spotMUs(self):
        mu = np.array([])
        for layer in self._layers:
            mu = np.concatenate((mu, layer.spotMUs))

        return mu

    @spotMUs.setter
    def spotMUs(self, mu: Sequence[float]):
        mu = np.array(mu)

        ind = 0
        for layer in self._layers:
            layer.spotMUs = mu[ind:ind + len(layer.spotMUs)]
            ind += len(layer.spotMUs)

    @property
    def spotTimings(self):
        timings = np.array([])
        for layer in self._layers:
            timings = np.concatenate((timings, layer.spotTimings))

        return timings

    @spotTimings.setter
    def spotTimings(self, t: Sequence[float]):
        t = np.array(t)

        ind = 0
        for layer in self._layers:
            layer.spotTimings = t[ind:ind + len(layer.spotTimings)]
            ind += len(layer.spotTimings)

    @property
    def spotIrradiationDurations(self):
        durations = np.array([])
        for layer in self._layers:
            durations = np.concatenate((durations, layer.spotIrradiationDurations))

        return durations

    @spotIrradiationDurations.setter
    def spotIrradiationDurations(self, t: Sequence[float]):
        t = np.array(t)

        if len(t) != self.numberOfSpots:
            raise ValueError(f'Cannot set spot durations of size {len(t)} to size {self.numberOfSpots}')

        ind = 0
        for layer in self._layers:
            layer.spotIrradiationDurations = t[ind:ind + layer.numberOfSpots]
            ind += layer.numberOfSpots

    @property
    def spotXY(self) -> np.ndarray:
        xy = np.array([])
        for layer in self._layers:
            layerXY = layer.spotXY
            if len(layerXY) <= 0:
                continue

            if len(xy) <= 0:
                xy = layerXY
            else:
                xy = np.concatenate((xy, layerXY))

        return xy

    @property
    def meterset(self) -> float:
        return np.sum(np.array([layer.meterset for layer in self._layers]))

    @property
    def numberOfSpots(self) -> int:
        return np.sum(np.array([layer.numberOfSpots for layer in self._layers]))

    def simplify(self, threshold: float = 0.0):
        """
        Simplify the layers by removing spots with a weight below the given threshold.

        Parameters
        ----------
        threshold: float (default: 0.0)
            threshold below which spots are removed
        """
        self._fusionDuplicates()

        for layer in self._layers:
            layer.simplify(threshold=threshold)

        # Remove empty layers
        self._layers = [layer for layer in self._layers if len(layer._mu) > 0]
        

    def reorderLayers(self, order: Optional[Union[str, Sequence[int]]] = 'decreasing'):
        """
        Reorder the layers.

        Parameters
        ----------
        order: str or list of int (default: 'decreasing')
            order of the layers. If 'decreasing' or 'scanAlgo', the layers are ordered by decreasing nominal energy.
            If a list of int, the layers are ordered according to the list.
        """
        if type(order) is str:
            if order == 'decreasing' or order == 'scanAlgo':
                order = np.argsort([layer.nominalEnergy for layer in self._layers])[::-1]
            else:
                raise ValueError(f"Reordering method {order} does not exist.")

        self._layers = [self._layers[i] for i in order]

    def _fusionDuplicates(self):
        if len(self) > 1:
            unique_nominalEnergies = [self._layers[0].nominalEnergy]
            ind = 1
            while ind < len(self._layers):
                current_nominalEnergy = self._layers[ind].nominalEnergy
                same_energy_layer = np.abs(np.array(unique_nominalEnergies) - current_nominalEnergy) < 0.05
                if np.any(same_energy_layer):
                    #fusion
                    match_ind = np.flatnonzero(same_energy_layer)[0] # first (and only) index respecting constraint 
                    if self._layers[ind].numberOfPaintings != self._layers[match_ind].numberOfPaintings:
                        print(f"Warning: numberOfPaintings different in layers with same nominal energy. Choosing the numberOfPaintings {self._layers[match_ind].numberOfPaintings}")
                    if self._layers[ind].rangeShifterSettings.__dict__ != self._layers[match_ind].rangeShifterSettings.__dict__:
                        print(f"Warning: rangeShifterSettings different in layers with same nominal energy. Choosing the rangeShifterSettings {self._layers[match_ind].rangeShifterSettings}")
                    if self._layers[ind].scalingFactor != self._layers[match_ind].scalingFactor:
                        print(f"Warning: scalingFactor different in layers with same nominal energy. Choosing scalingFactor {self._layers[match_ind].scalingFactor}")
                                
                    self._layers[match_ind]._x = np.concatenate((self._layers[match_ind]._x, self._layers[ind]._x))
                    self._layers[match_ind]._y = np.concatenate((self._layers[match_ind]._y, self._layers[ind]._y))
                    self._layers[match_ind]._mu = np.concatenate((self._layers[match_ind]._mu, self._layers[ind]._mu))
                    if len(self._layers[match_ind]._startTime)>0 or len(self._layers[ind]._startTime)>0:
                        #check both are non empty
                        if len(self._layers[match_ind]._startTime)==0 or len(self._layers[ind]._startTime)==0:
                            print(f"When attempting to merge layers at energy {current_nominalEnergy}, one layer contain delivery timings while the other do not.")
                        self._layers[match_ind]._startTime = np.concatenate((self._layers[match_ind]._startTime, self._layers[ind]._startTime))
                    if len(self._layers[match_ind]._irradiationDuration)>0 or len(self._layers[ind]._irradiationDuration)>0:
                        #check both are non empty
                        if len(self._layers[match_ind]._irradiationDuration)==0 or len(self._layers[ind]._irradiationDuration)==0:
                            print(f"When attempting to merge layers at energy {current_nominalEnergy}, one layer contain irradiation durations while the other do not.")
                        self._layers[match_ind]._irradiationDuration = np.concatenate((self._layers[match_ind]._irradiationDuration, self._layers[ind]._irradiationDuration))
                    self.removeLayer(self._layers[ind])
                else:
                    unique_nominalEnergies.append(current_nominalEnergy)
                    ind += 1

    def copy(self):
        return copy.deepcopy(self)

    def createEmptyBeamWithSameMetaData(self):
        """
        Create an empty beam with the same metadata (gantry angle, couch angle, etc.).
        """
        beam = self.copy()
        beam._layers = []
        return beam


class PlanIonLayerBeamCase(unittest.TestCase):
    def testFusionDuplicates(self):
        from opentps.core.data.plan import PlanIonLayer

        beam = PlanIonBeam()
        beam.gantryAngle = 0
        beam.couchAngle = 0
        layer = PlanIonLayer(nominalEnergy=100.)
        x = [0, 2, 1, 3]
        y = [1, 2, 2, 0]
        mu = [0.2, 0.5, 0.3, 0.1]
        layer.appendSpot(x, y, mu)
        beam.appendLayer(layer)

        layer2 = PlanIonLayer(nominalEnergy=110.)
        beam.appendLayer(layer2)

        layer3 = PlanIonLayer(nominalEnergy=100.)
        x = [1, 3, 2, 4]
        y = [2, 3, 3, 1]
        mu = [0.3, 0.6, 0.4, 0.2]
        layer3.appendSpot(x, y, mu)
        beam.appendLayer(layer3)

        beam._fusionDuplicates()
        self.assertEqual(len(beam._layers),2)
        np.testing.assert_array_equal(beam._layers[0].spotX, np.array([0, 2, 1, 3, 1, 3, 2, 4]))
        np.testing.assert_array_equal(beam._layers[1].spotX, np.array([]))
        np.testing.assert_array_equal(beam._layers[0].spotY, np.array([1, 2, 2, 0, 2, 3, 3, 1]))
        np.testing.assert_array_equal(beam._layers[1].spotY, np.array([]))
        np.testing.assert_array_almost_equal(beam._layers[0].spotMUs, np.array([0.2, 0.5, 0.3, 0.1, 0.3, 0.6, 0.4, 0.2]))
        np.testing.assert_array_equal(beam._layers[1].spotMUs, np.array([]))


if __name__ == '__main__':
    unittest.main()
