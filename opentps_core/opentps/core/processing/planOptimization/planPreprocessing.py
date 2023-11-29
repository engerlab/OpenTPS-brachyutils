import copy
from typing import Sequence

import numpy as np

from opentps.core.data.plan._planIonBeam import PlanIonBeam
from opentps.core.data.plan._planIonLayer import PlanIonLayer
from opentps.core.data.plan._planIonSpot import PlanIonSpot
from opentps.core.data.plan._rtPlan import RTPlan

'''
Extend rtplan with attributs .layers and .spots to access directly global id and energy for each beam, layer and spot without looping. 
'''

def extendPlanLayers(plan: RTPlan) -> RTPlan:
    """
    Extends the plan with a list of layers and spots for each beam.

    Parameters
    ----------
    plan : RTPlan
        The plan to extend.

    Returns
    -------
    RTPlan
        The extended plan.
    """
    plan._layers = []
    plan._spots = []

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
                plan._spots.append(spot)

            layerID += 1
            plan._layers.append(outLayer)

class ExtendedBeam(PlanIonBeam):
    """
    Class to extend the PlanIonBeam class with a list of layers. Inherits from PlanIonBeam.

    Attributes
    ----------
    laverIndices : Sequence[int]
        The indices of the layers in the beam.
    """
    def __init__(self):
        super().__init__()

    @classmethod
    def fromBeam(cls, beam: PlanIonBeam):
        """
        Creates a new ExtendedBeam from a PlanIonBeam.

        Parameters
        ----------
        beam : PlanIonBeam
            The beam to copy.

        Returns
        -------
        ExtendedBeam
            The new beam.
        """
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
    """
    Class to extend the PlanIonLayer class with a list of spots. Inherits from PlanIonLayer.

    Attributes
    ----------
    spots : Sequence[PlanIonSpot]
        The spots in the layer.
    spotIndices : Sequence[int]
        The indices of the spots in the layer.
    id : int
        The id of the layer.
    beamID : int
        The id of the beam the layer belongs to.
    """
    def __init__(self, nominalEnergy: float = 0.0):
        super().__init__(nominalEnergy=nominalEnergy)

        self._spots = []

        self.id = 0
        self.beamID = 0

    @classmethod
    def fromLayer(cls, layer: PlanIonLayer):
        """
        Creates a new ExtendedPlanIonLayer from a PlanIonLayer.

        Parameters
        ----------
        layer : PlanIonLayer
            The layer to copy.

        Returns
        -------
        ExtendedPlanIonLayer
            The new layer.
        """
        newLayer = cls(layer.nominalEnergy)
        spotXY = list(layer.spotXY)
        spotMUs = layer.spotMUs

        for s in range(layer.numberOfSpots):
            newLayer.appendSpot(spotXY[s][0], spotXY[s][1], spotMUs[s])
            spot = PlanIonSpot()
            newLayer._spots.append(spot)

        newLayer._startTime = np.array(layer._startTime)
        newLayer._irradiationDuration = np.array(layer._irradiationDuration)

        return newLayer

    @property
    def spots(self) -> Sequence[PlanIonSpot]:
        # For backwards compatibility but we can now access each spot with indexing brackets
        return [spot for spot in self._spots]

    @property
    def spotIndices(self) -> Sequence[int]:
        return [spot.id for spot in self._spots]
