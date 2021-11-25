import numpy as np
import json
import scipy.ndimage
import pydicom
import time
import logging
import math

try:
  import sparse_dot_mkl
  use_MKL = 1
except:
  use_MKL = 0

from Processing.RTplan import *
from Processing.C_libraries.libRayTracing_wrapper import *


logger = logging.getLogger(__name__)

class PlanDesign:
    def __init__(self, ct, targetMask, scanner, rangeShifters = [], targetMargin=5.0, spotSpacing=5.0, layerSpacing=5.0, proximalLayers=1, distalLayers=1, alignLayersToSpacing = False):
        self.ct = ct
        self.targetMask = targetMask
        self.scanner = scanner
        self.rangeShifters = rangeShifters
        self.targetMargin = targetMargin
        self.spotSpacing= spotSpacing
        self.layerSpacing = layerSpacing
        self.proximalLayers = proximalLayers
        self.distalLayers = distalLayers
        self.alignLayersToSpacing = alignLayersToSpacing
    
    def createPlanStructure(self, beamNames, gantryAngles, couchAngles):
        start = time.time()

        plan = RTplan()
        plan.sopInstanceUID = pydicom.uid.generate_uid()
        plan.seriesInstanceUID = plan.SOPInstanceUID + ".1"
        plan.planName = "NewPlan"
        plan.modality = "Ion therapy"
        plan.radiationType = "Proton"
        plan.scanMode = "MODULATED"
        plan.treatmentMachineName = "Unknown"
        plan.numberOfFractionsPlanned = 1

        # compute isocenter position as center of the target
        isoCenter = self.computeIsocenter()

        # compute RTV = dilated target for spot placement
        targetMarginX = targetMargin / self.ct.pixelSpacing[0] # voxels
        targetMarginY = targetMargin / self.ct.pixelSpacing[1] # voxels
        targetMarginZ = targetMargin / self.ct.pixelSpacing[2] # voxels
        targetMarginSize = 2*np.ceil(np.array([targetMarginY, targetMarginX, targetMarginZ])).astype(int)+1 # size of the structuring element
        struct = np.zeros(tuple(targetMarginSize)).astype(bool)
        for i in range(targetMarginSize[0]):
          for j in range(targetMarginSize[1]):
            for k in range(targetMarginSize[2]):
              y = i - math.floor(targetMarginSize[0]/2)
              x = j - math.floor(targetMarginSize[1]/2)
              z = k - math.floor(targetMarginSize[2]/2)
              if(y**2/targetMarginY**2 + x**2/targetMarginX**2 + z**2/targetMarginZ**2 <= 1): # generate ellipsoid structuring element
                struct[i,j,k] = True
        targetMarginMask = scipy.ndimage.binary_dilation(self.targetMask, structure=struct).astype(self.targetMask.dtype)

        # initialize each beam
        for b in range(len(gantryAngles)):
          plan.beams.append(PlanIonBeam())
          plan.beams[b].beamName = beamNames[b]
          plan.beams[b].gantryAngle = gantryAngles[b]
          plan.beams[b].patientSupportAngle = couchAngles[b]
          plan.beams[b].isocenterPosition = isoCenter
          plan.beams[b].spotSpacing = self.spotSpacing
          plan.beams[b].layerSpacing = self.layerSpacing
          if(self.rangeShifters != [] and self.rangeShifters[b] != "None"):
            plan.beams[b].rangeShifterID = self.rangeShifters[b].id
            plan.beams[b].rangeShifterType = self.rangeShifters[b].type

        # spot placement
        plan = self.placeSpots(plan)

        #previous_energy = 999
        for beam in plan.beams:
          beam.layers.sort(reverse=True, key=(lambda element: element.nominalBeamEnergy))
          
          # # arc pt
          # for l in range(len(beam.layers)):
          #   if(beam.layers[l].nominalBeamEnergy < previous_energy):
          #     previousEnergy = beam.layers[l].nominalBeamEnergy
          #     beam.layers = [beam.layers[l]]
          #     print(beam.layers[0].nominalBeamEnergy)
          #     break

          # if len(beam.layers) > 1:
          #   previousEnergy = beam.layers[0].nominalBeamEnergy
          #   beam.layers = [beam.layers[0]]
          #   print(beam.layers[0].nominalBeamEnergy)


        plan.isLoaded = 1

        logger.info("New plan created in " + str(time.time()-start) + " sec")
        logger.info("Number of spots: " + str(plan.numberOfSpots))

        return plan

    def placeSpots(self, plan):
		spr = SPRimage()
        spr.convertCTtoSPR(self.ct, self.scanner)

        imgBordersX = [spr.imagePositionPatient[0], spr.imagePositionPatient[0] + spr.gridSize[0] * spr.pixelSpacing[0]]
        imgBordersY = [spr.imagePositionPatient[1], spr.imagePositionPatient[1] + spr.gridSize[1] * spr.pixelSpacing[1]]
        imgBordersZ = [spr.imagePositionPatient[2], spr.imagePositionPatient[2] + spr.gridSize[2] * spr.pixelSpacing[2]]

        plan.numberOfSpots = 0

        for b in range(len(plan.beams)):
          beam = plan.beams[b]

          # generate hexagonal spot grid around isocenter
          spotGrid = self.generateHexagonalspotGrid(beam.isocenterPosition, beam.spotSpacing, beam.gantryAngle, beam.patientSupportAngle)
          numSpots = len(spotGrid["x"])

          # compute direction vector
          u,v,w = 1e-10, 1.0, 1e-10 # BEV to 3D coordinates
          [u,v,w] = self.rotateVector([u,v,w], math.radians(beam.gantryAngle), 'z') # rotation for gantry angle
          [u,v,w] = self.rotateVector([u,v,w], math.radians(beam.patientSupportAngle), 'y') # rotation for couch angle

          # prepare raytracing: translate initial positions at the self.ct image border
          for s in range(numSpots):
            translation = np.array([1.0, 1.0, 1.0])
            translation[0] = (spotGrid["x"][s] - imgBordersX[int(u<0)]) / u
            translation[1] = (spotGrid["y"][s] - imgBordersY[int(v<0)]) / v
            translation[2] = (spotGrid["z"][s] - imgBordersZ[int(w<0)]) / w
            translation = translation.min()
            spotGrid["x"][s] = spotGrid["x"][s] - translation * u
            spotGrid["y"][s] = spotGrid["y"][s] - translation * v
            spotGrid["z"][s] = spotGrid["z"][s] - translation * w

          # transport each spot until it reaches the target
          transportSpotsToTarget(spr, self.targetMask, spotGrid, [u,v,w])

          # remove spots that didn't reach the target
          minWET = 9999999
          for s in range(numSpots-1, -1, -1):
            if(spotGrid["WET"][s] < 0):
              spotGrid["BEVx"].pop(s)
              spotGrid["BEVy"].pop(s)
              spotGrid["x"].pop(s)
              spotGrid["y"].pop(s)
              spotGrid["z"].pop(s)
              spotGrid["WET"].pop(s)
            else:
              if(self.rangeShifters != [] and self.rangeShifters[b] != "None" and self.rangeShifters[b].wet > 0.0): spotGrid["WET"][s] += self.rangeShifters[b].wet
              if(spotGrid["WET"][s] < minWET): minWET = spotGrid["WET"][s]
              if(alignLayersToSpacing): minWET = round(minWET/beam.layerSpacing)*beam.layerSpacing

          # raytracing of remaining spots to define energy layers
          transportSpotsInsideTarget(spr, self.targetMask, spotGrid, [u,v,w], minWET, beam.layerSpacing)

          # process valid spots
          numSpots = len(spotGrid["x"])
          for s in range(numSpots):
            initNumLayers = len(spotGrid["EnergyLayers"][s])
            if(initNumLayers == 0): continue

            # additional layers in proximal and distal directions:
            if(self.proximalLayers > 0):
              minEnergy = min(spotGrid["EnergyLayers"][s])
              minWET = spr.energyToRange(minEnergy)*10
              for l in range(self.proximalLayers):
                minWET -= beam.layerSpacing
                spotGrid["EnergyLayers"][s].append(spr.rangeToEnergy(minWET/10))
            if(self.distalLayers > 0):
              maxEnergy = max(spotGrid["EnergyLayers"][s])
              maxWET = spr.energyToRange(maxEnergy)*10
              for l in range(self.distalLayers):
                maxWET += beam.layerSpacing
                spotGrid["EnergyLayers"][s].append(spr.rangeToEnergy(maxWET/10))

            # generate plan structure
            for energy in spotGrid["EnergyLayers"][s]:
              plan.numberOfSpots += 1
              layerFound = 0
              for layer in beam.layers:
                if(abs(layer.nominalBeamEnergy - energy) < 0.05):
                  # add spot to existing layer
                  layer.scanSpotPositionMapX.append(spotGrid["BEVx"][s])
                  layer.scanSpotPositionMapY.append(spotGrid["BEVy"][s])
                  layer.scanSpotMetersetWeights.append(1.0)
                  layer.spotMU.append(1.0)
                  layerFound = 1

              if(layerFound == 0):
                # add new layer
                beam.layers.append(PlanIonLayer())
                beam.layers[-1].nominalBeamEnergy = energy
                beam.layers[-1].scanSpotPositionMapX.append(spotGrid["BEVx"][s])
                beam.layers[-1].scanSpotPositionMapY.append(spotGrid["BEVy"][s])
                beam.layers[-1].scanSpotMetersetWeights.append(1.0)
                beam.layers[-1].spotMU.append(1.0)

                if(self.rangeShifters != [] and self.rangeShifters[b] != "None" and self.rangeShifters[b].wet > 0.0):
                  beam.layers[-1].rangeShifterSetting = 'IN'
                  beam.layers[-1].isocenterToRangeShifterDistance = 300.0 #TODO: raytrace distance from iso to body contour and add safety margin
                  beam.layers[-1].rangeShifterWaterEquivalentThickness = self.rangeShifters[b].wet
        return plan

    def generateHexagonalspotGrid(self, spotSpacing, gantryAngle, couchAngle):
		fov = 400 # max field size on IBA P+ is 30x40 cm
        numSpotX = math.ceil(fov / spotSpacing)
        numSpotY = math.ceil(fov / (spotSpacing * math.cos(math.pi/6)))

        spotGrid = {}
        spotGrid["BEVx"] = []
        spotGrid["BEVy"] = []
        spotGrid["x"] = []
        spotGrid["y"] = []
        spotGrid["z"] = []
        spotGrid["WET"] = []
        spotGrid["EnergyLayers"] = []

        for i in range(numSpotX):
          for j in range(numSpotY):
            spot = {}

            # coordinates in Beam-eye-view
            spotGrid["BEVx"].append( (i-round(numSpotX/2)+(j%2)*0.5)* spotSpacing )
            spotGrid["BEVy"].append( (j-round(numSpotY/2)) * spotSpacing * math.cos(math.pi/6) )

            # 3D coordinates
            x,y,z = spotGrid["BEVx"][-1], 0, spotGrid["BEVy"][-1]

            # rotation for gantry angle (around Z axis)
            [x,y,z] = self.rotateVector([x,y,z], math.radians(gantryAngle), 'z')

            # rotation for couch angle (around Y axis)
            [x,y,z] = self.rotateVector([x,y,z], math.radians(couchAngle), 'y')

            # Dicom CT coordinates
            spotGrid["x"].append( x + isoCenter[0] )
            spotGrid["y"].append( y + isoCenter[1] )
            spotGrid["z"].append( z + isoCenter[2] )

        return spotGrid

    def rotateVector(self, vec, angle, axis):
		if axis == 'x':
    		x = vec[0]
    		y = vec[1] * math.cos(angle) - vec[2] * math.sin(angle)
    		z = vec[1] * math.sin(angle) + vec[2] * math.cos(angle)
  		elif axis ==  'y':
    		x = vec[0] * math.cos(angle) + vec[2] * math.sin(angle)
    		y = vec[1]
    		z = -vec[0] * math.sin(angle) + vec[2] * math.cos(angle)
  		elif axis == 'z':
    		x = vec[0] * math.cos(angle) - vec[1] * math.sin(angle)
    		y = vec[0] * math.sin(angle) + vec[1] * math.cos(angle)
    		z = vec[2]

  		return [x,y,z]

    def computeIsocenter(self):
    	maskX,maskY,maskZ = np.nonzero(self.targetMask)
    	return [np.mean(self.ct.voxelX[maskX]), np.mean(self.ct.voxelY[maskY]), np.mean(self.ct.voxelZ[maskZ])]
