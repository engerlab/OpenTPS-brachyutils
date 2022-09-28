import math

import numpy as np
from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.plan._planIonLayer import PlanIonLayer
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.processing.C_libraries.libRayTracing_wrapper import transport_spots_to_target, \
    transport_spots_inside_target
from opentps.core.processing.rangeEnergy import energyToRange, rangeToEnergy


class BeamInitializer:
    def __init__(self):
        self.spotSpacing = 5.
        self.layerSpacing = 2.
        self.targetMargin = 0.
        self.rangeShifter = None
        self.beam = None

        self.calibration: AbstractCTCalibration = None

    def initializeBeam(self):

        # generate hexagonal spot grid around isocenter
        spotGrid = self._defineHexagSpotGridAroundIsocenter()
        numSpots = len(spotGrid["x"])

        # compute direction vector
        u, v, w = 1e-10, 1.0, 1e-10  # BEV to 3D coordinates
        [u, v, w] = self._rotateVector([u, v, w], math.radians(self.beam.gantryAngle), 'z')  # rotation for gantry angle
        [u, v, w] = self._rotateVector([u, v, w], math.radians(self.beam.couchAngle), 'y')  # rotation for couch angle

        # prepare raytracing: translate initial positions at the CT image border
        for s in range(numSpots):
            translation = np.array([1.0, 1.0, 1.0])
            translation[0] = (spotGrid["x"][s] - self.imgBordersX[int(u < 0)]) / u
            translation[1] = (spotGrid["y"][s] - self.imgBordersY[int(v < 0)]) / v
            translation[2] = (spotGrid["z"][s] - self.imgBordersZ[int(w < 0)]) / w
            translation = translation.min()
            spotGrid["x"][s] = spotGrid["x"][s] - translation * u
            spotGrid["y"][s] = spotGrid["y"][s] - translation * v
            spotGrid["z"][s] = spotGrid["z"][s] - translation * w

        # transport each spot until it reaches the target
        transport_spots_to_target(self.rspImage, self.targetMask, spotGrid, [u, v, w])

        # remove spots that didn't reach the target
        minWET = 9999999
        for s in range(numSpots - 1, -1, -1):
            if spotGrid["WET"][s] < 0:
                spotGrid["BEVx"].pop(s)
                spotGrid["BEVy"].pop(s)
                spotGrid["x"].pop(s)
                spotGrid["y"].pop(s)
                spotGrid["z"].pop(s)
                spotGrid["WET"].pop(s)
            else:
                if self.beam.rangeShifter and self.beam.rangeShifter.WET > 0.0: spotGrid["WET"][
                    s] += self.rangeShifter.WET
                if spotGrid["WET"][s] < minWET: minWET = spotGrid["WET"][s]
                if self.layersToSpacingAlignment: minWET = round(minWET / self.layerSpacing) * self.layerSpacing

        # raytracing of remaining spots to define energy layers
        transport_spots_inside_target(self.rspImage, self.targetMask, spotGrid, [u, v, w], minWET, self.layerSpacing)

        # process valid spots
        numSpots = len(spotGrid["x"])
        for s in range(numSpots):
            initNumLayers = len(spotGrid["EnergyLayers"][s])
            if initNumLayers == 0: continue

            # additional layers in proximal and distal directions:
            if self.proximalLayers > 0:
                minEnergy = min(spotGrid["EnergyLayers"][s])
                minWET = energyToRange(minEnergy) * 10
                for l in range(self.proximalLayers):
                    minWET -= self.layerSpacing
                    spotGrid["EnergyLayers"][s].append(rangeToEnergy(minWET / 10))
            if self.distalLayers > 0:
                maxEnergy = max(spotGrid["EnergyLayers"][s])
                maxWET = energyToRange(maxEnergy) * 10
                for l in range(self.distalLayers):
                    maxWET += self.layerSpacing
                    spotGrid["EnergyLayers"][s].append(rangeToEnergy(maxWET / 10))

            # generate plan structure
            for energy in spotGrid["EnergyLayers"][s]:
                layerFound = 0
                for layer in self.beam.layers:
                    if abs(layer.nominalEnergy - energy) < 0.05:
                        # add spot to existing layer
                        layer.appendSpot(spotGrid["BEVx"][s], spotGrid["BEVy"][s], 1.)
                        layerFound = 1

                if layerFound == 0:
                    # add new layer
                    layer = PlanIonLayer(energy)
                    layer.appendSpot(spotGrid["BEVx"][s], spotGrid["BEVy"][s], 1.)

                    if self.beam.rangeShifter and self.beam.rangeShifter.WET > 0.0:
                        layer.rangeShifterSettings.rangeShifterSetting = 'IN'
                        layer.rangeShifterSettings.isocenterToRangeShifterDistance = 300.0  # TODO: raytrace distance from iso to body contour and add safety margin
                        layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness = self.beam.rangeShifter.WET
                    self.beam.appendLayer(layer)

    def _defineHexagSpotGridAroundIsocenter(self):
        FOV = 400  # max field size on IBA P+ is 30x40 cm
        numSpotX = math.ceil(FOV / self.spotSpacing)
        numSpotY = math.ceil(FOV / (self.spotSpacing * math.cos(math.pi / 6)))

        spotGrid = {"BEVx": [], "BEVy": [], "x": [], "y": [], "z": [], "WET": [], "EnergyLayers": []}

        for i in range(numSpotX):
            for j in range(numSpotY):
                spot = {}

                # coordinates in Beam-eye-view
                spotGrid["BEVx"].append((i - round(numSpotX / 2) + (j % 2) * 0.5) * self.spotSpacing)
                spotGrid["BEVy"].append((j - round(numSpotY / 2)) * self.spotSpacing * math.cos(math.pi / 6))

                # 3D coordinates
                x, y, z = spotGrid["BEVx"][-1], 0, spotGrid["BEVy"][-1]

                # rotation for gantry angle (around Z axis)
                [x, y, z] = self._rotateVector([x, y, z], math.radians(self.beam.gantryAngle), 'z')

                # rotation for couch angle (around Y axis)
                [x, y, z] = self._rotateVector([x, y, z], math.radians(self.beam.couchAngle), 'y')

                # Dicom CT coordinates
                spotGrid["x"].append(x + self.beam.isocenterPosition[0])
                spotGrid["y"].append(y + self.beam.isocenterPosition[1])
                spotGrid["z"].append(z + self.beam.isocenterPosition[2])
        return spotGrid

    def _rotateVector(self, vec, angle, axis):
        if axis == 'x':
            x = vec[0]
            y = vec[1] * math.cos(angle) - vec[2] * math.sin(angle)
            z = vec[1] * math.sin(angle) + vec[2] * math.cos(angle)
        elif axis == 'y':
            x = vec[0] * math.cos(angle) + vec[2] * math.sin(angle)
            y = vec[1]
            z = -vec[0] * math.sin(angle) + vec[2] * math.cos(angle)
        elif axis == 'z':
            x = vec[0] * math.cos(angle) - vec[1] * math.sin(angle)
            y = vec[0] * math.sin(angle) + vec[1] * math.cos(angle)
            z = vec[2]

        return [x, y, z]


class PlanInitializer:
    def __init__(self):
        self.ctCalibration: AbstractCTCalibration = None
        self.ct: CTImage = None
        self.plan: RTPlan = None
        self.targetMask: ROIMask = None

        self._beamInitializer = BeamInitializer()

    def placeSpots(self, spotSpacing: float, layerSpacing: float, targetMargin: float = 0.,
                   layersToSpacingAlignment=False, proximalLayers=1, distalLayers=1):
        self._beamInitializer.calibration = self.ctCalibration
        self._beamInitializer.spotSpacing = spotSpacing
        self._beamInitializer.layerSpacing = layerSpacing
        self._beamInitializer.targetMargin = targetMargin
        self._beamInitializer.layersToSpacingAlignment = layersToSpacingAlignment
        self._beamInitializer.proximalLayers = proximalLayers
        self._beamInitializer.distalLayers = distalLayers

        from opentps.core.data.images._rspImage import RSPImage
        roiDilated = ROIMask.fromImage3D(self.targetMask, patient=None)
        roiDilated.dilate(radius=targetMargin)
        self._beamInitializer.targetMask = roiDilated

        rspImage = RSPImage.fromCT(self.ct, self.ctCalibration, energy=100.)
        self._beamInitializer.rspImage = rspImage

        imgBordersX = [rspImage.origin[0], rspImage.origin[0] + rspImage.gridSize[0] * rspImage.spacing[0]]
        imgBordersY = [rspImage.origin[1], rspImage.origin[1] + rspImage.gridSize[1] * rspImage.spacing[1]]
        imgBordersZ = [rspImage.origin[2], rspImage.origin[2] + rspImage.gridSize[2] * rspImage.spacing[2]]

        self._beamInitializer.imgBordersX = imgBordersX
        self._beamInitializer.imgBordersY = imgBordersY
        self._beamInitializer.imgBordersZ = imgBordersZ

        for beam in self.plan:
            beam.removeLayer(beam.layers)

            self._beamInitializer.beam = beam
            self._beamInitializer.initializeBeam()
