
__all__ = ['PlanIonBeam']


import copy
from typing import Optional, Sequence, Union

import numpy as np

from Core.Data.Plan._planIonLayer import PlanIonLayer
from Core.Data.Plan._rangeShifter import RangeShifter


class PlanIonBeam:
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

    def __getitem__(self, layerNb) -> PlanIonLayer:
        return self._layers[layerNb]

    def __len__(self):
        return len(self._layers)

    def __str__(self):
        s = ''
        for layer in self._layers:
            s += 'Layer\n'
            s += str(layer)

        return s

    def __deepcopy__(self, memodict={}):
        newBeam = PlanIonBeam()

        memodict[id(self)] = newBeam

        newBeam._deepCopyProperties(self, memodict)

        return newBeam

    def _deepCopyProperties(self, otherBeam, memodict):
        self._layers = [layer.__deepcopy__(memodict) for layer in otherBeam._layers]

        self.name = otherBeam.name
        self.isocenterPosition = np.array(otherBeam.isocenterPosition)
        self.gantryAngle = otherBeam.gantryAngle
        self.couchAngle = otherBeam.couchAngle
        self.id = otherBeam.id
        self.rangeShifter = copy.deepcopy(otherBeam.rangeShifter, memodict)
        self.seriesInstanceUID = otherBeam.seriesInstanceUID


    @property
    def layers(self) -> Sequence[PlanIonLayer]:
        # For backwards compatibility but we can now access each layer with indexing brackets
        return [layer for layer in self._layers]

    def appendLayer(self, layer: PlanIonLayer):
        self._layers.append(layer)

    def removeLayer(self, layer: Union[PlanIonLayer, Sequence[PlanIonLayer]]):
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
    def spotXY(self) -> np.ndarray:
        xy = np.array([])
        for layer in self._layers:
            layerXY = list(layer.spotXY)
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
        self._fusionDuplicates()

        for layer in self._layers:
            layer.simplify(threshold=threshold)

    def reorderLayers(self, order: Optional[Union[str, Sequence[int]]] = 'decreasing'):
        if type(order) is str:
            if order == 'decreasing' or order == 'scanAlgo':
                order = np.argsort([layer.nominalEnergy for layer in self._layers])[::-1]
            else:
                raise ValueError(f"Reordering method {order} does not exist.")

        self._layers = [self._layers[i] for i in order]

    def _fusionDuplicates(self):
        # TODO
        raise NotImplementedError()

    def copy(self):
        return copy.deepcopy(self)

    def createEmptyBeamWithSameMetaData(self):
        beam = self.copy()
        beam._layers = []
        return beam
