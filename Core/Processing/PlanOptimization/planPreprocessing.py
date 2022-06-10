import copy
from typing import Sequence

import numpy as np

from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.planIonSpot import PlanIonSpot
from Core.Data.Plan.rtPlan import RTPlan


def extendPlanLayers(plan:RTPlan) -> RTPlan:
    outPlan = copy.deepcopy(plan)

    layerID = 0
    spotID = 0
    for beamID, referencBeam in enumerate(plan):
        outBeam = outPlan[beamID]
        outBeam.removeLayer(outBeam.layers) # Remove all layers

        for referenceLayer in referencBeam:
            outLayer = ExtendedPlanIonLayer.fromLayer(referenceLayer)

            for spot in outLayer.spots:
                spot.id = spotID
                spot.beamID = beamID
                spot.layerID = layerID
                spot.energy = outLayer.nominalEnergy

                spotID += 1

            layerID += 1

    return outPlan

class ExtendedPlanIonLayer(PlanIonLayer):
    def __init__(self, nominalEnergy:float=0.0):
        super().__init__(nominalEnergy=nominalEnergy)

        self._spots = []

        self.id =0
        self.beamID = 0

    @classmethod
    def fromLayer(cls, layer:PlanIonLayer):
        newLayer = cls(layer.nominalEnergy)
        spotXY = list(layer.spotXY)
        spotWeights = layer.spotWeights

        for s in range(layer.numberOfSpots):
            newLayer.appendSpot(spotXY[s][0], spotXY[s][1], spotWeights[s])
            spot = PlanIonSpot()
            newLayer._spots.append(spot)

        newLayer._timings = np.array(layer._timings)

        return newLayer

    @property
    def spots(self) -> Sequence[PlanIonSpot]:
        # For backwards compatibility but we can now access each spot with indexing brackets
        return [spot for spot in self._spots]

    @property
    def spotIndices(self) -> Sequence[int]:
        return [spot.id for spot in self._spots]
