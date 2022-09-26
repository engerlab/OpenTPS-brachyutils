import copy
from typing import Sequence

import numpy as np

from opentps.core.data.plan._planIonBeam import PlanIonBeam
from opentps.core.data.plan._planIonLayer import PlanIonLayer
from opentps.core.data.plan._planIonSpot import PlanIonSpot
from opentps.core.data.plan._rtPlan import RTPlan


def extendPlanLayers(plan: RTPlan) -> RTPlan:
    outPlan = copy.deepcopy(plan)

    layerID = 0
    spotID = 0
    for beamID, referenceBeam in enumerate(plan):
        outBeam = ExtendedBeam.fromBeam(referenceBeam)
        outBeam.removeLayer(outBeam.layers)  # Remove all layers
        outBeam.id = beamID

        for referenceLayer in referenceBeam:
            outLayer = ExtendedPlanIonLayer.fromLayer(referenceLayer)
            outLayer.id = layerID
            outLayer.beamID = beamID

            for spot in outLayer.spots:
                spot.id = spotID
                spot.beamID = beamID
                spot.layerID = layerID
                spot.energy = outLayer.nominalEnergy

                spotID += 1
                outPlan.appendSpotAccum(spot)

            layerID += 1
            outPlan.appendLayerAccum(outLayer)

    return outPlan


class ExtendedBeam(PlanIonBeam):
    def __init__(self):
        super().__init__()

    @classmethod
    def fromBeam(cls, beam: PlanIonBeam):
        newBeam = cls()

        newBeam.name = beam.name
        newBeam.isocenterPosition = beam.isocenterPosition
        newBeam.gantryAngle = beam.gantryAngle
        newBeam.couchAngle = beam.couchAngle
        newBeam.rangeShifter = beam.rangeShifter
        newBeam.seriesInstanceUID = beam.seriesInstanceUID

        for layer in beam:
            newBeam.appendLayer(layer)

        return newBeam

    @property
    def layersIndices(self) -> Sequence[int]:
        return [layer.id for layer in self.layers]


class ExtendedPlanIonLayer(PlanIonLayer):
    def __init__(self, nominalEnergy: float = 0.0):
        super().__init__(nominalEnergy=nominalEnergy)

        self._spots = []

        self.id = 0
        self.beamID = 0

    @classmethod
    def fromLayer(cls, layer: PlanIonLayer):
        newLayer = cls(layer.nominalEnergy)
        spotXY = list(layer.spotXY)
        spotMUs = layer.spotMUs

        for s in range(layer.numberOfSpots):
            newLayer.appendSpot(spotXY[s][0], spotXY[s][1], spotMUs[s])
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
