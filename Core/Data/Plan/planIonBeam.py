from typing import Optional

import numpy as np

from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rangeShifter import RangeShifter


class PlanIonBeam:
    def __init__(self):
        self.name = ""
        self.isocenterPosition = [0, 0, 0]
        self.gantryAngle = 0.0
        self.patientSupportAngle = 0.0
        self._rangeShifter = None
        self._layers = []

        self.seriesInstanceUID = ""

    def  __getitem__(self, layerNb):
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
    def rangeShifter(self) -> Optional[RangeShifter]:
        return self._rangeShifter

    @rangeShifter.setter
    def rangeShifter(self, rs:Optional[RangeShifter]):
        self._rangeShifter = rs

    def appendLayer(self, layer: PlanIonLayer):
        self._layers.append(layer)

    def removeLayer(self, layer: PlanIonLayer):
        self._layers.remove(layer)

    @property
    def meterset(self) -> int:
        return np.sum(np.array([layer.meterset for layer in self._layers]))

    def simplify(self, threshold:float=0.0):
        self._fusionDuplicates()

        for layer in self._layers:
            layer.simplify(threshold=threshold)

    def _fusionDuplicates(self):
        #TODO
        raise NotImplementedError()