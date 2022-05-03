import copy
from typing import Optional, Sequence, Union

import numpy as np

from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rangeShifter import RangeShifter


class PlanIonBeam:
    def __init__(self):
        self._layers = []

        self.name = ""
        self.isocenterPosition = [0, 0, 0]
        self.gantryAngle = 0.0
        self.patientSupportAngle = 0.0
        self.rangeShifter: Optional[RangeShifter] = None
        self.seriesInstanceUID = ""

    def  __getitem__(self, layerNb) -> PlanIonLayer:
        return self._layers[layerNb]

    def __len__(self):
        return len(self._layers)

    def __str__(self):
        s = ''
        for layer in self._layers:
            s += 'Layer\n'
            s += str(layer)

        return s

    @property
    def layers(self) -> Sequence[PlanIonLayer]:
        # For backwards compatibility but we can now access each layer with indexing brackets
        return [layer for layer in self._layers]

    def appendLayer(self, layer:PlanIonLayer):
        self._layers.append(layer)

    def removeLayer(self, layer:Union[PlanIonLayer, Sequence[PlanIonLayer]]):
        if isinstance(layer, Sequence):
            layers = layer
            for layer in layers:
                self.removeLayer(layer)
            return

        self._layers.remove(layer)

    @property
    def spotWeights(self):
        weights = np.array([])
        for layer in self._layers:
            weights = np.concatenate((weights, layer.spotWeights))

        return weights

    @spotWeights.setter
    def spotWeights(self, w: Sequence[float]):
        w = np.array(w)

        ind = 0
        for layer in self._layers:
            layer.spotWeights = w[ind:ind+len(layer.spotWeights)]
            ind += len(layer.spotWeights)

    @property
    def meterset(self) -> float:
        return np.sum(np.array([layer.meterset for layer in self._layers]))

    def simplify(self, threshold:float=0.0):
        self._fusionDuplicates()

        for layer in self._layers:
            layer.simplify(threshold=threshold)

    def _fusionDuplicates(self):
        #TODO
        raise NotImplementedError()