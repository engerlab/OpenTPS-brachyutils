import json
from Process.RTplan import *

'''
Class to convert openTPS plan into json plan (input for scanAlgo) 

Usage:

from Process.jsonPlan import *

# load OpenTPS plan
file_path = "Plan_OpenTPS.tps"
plan = RTplan()
plan.load(file_path)

jsonPlans = JsonPlans(plan)
# Create 1 json file per beam
jsonPlans.allBeams()

'''



class JsonPlans:
    def __init__(self,plan, Gantry = "PPlus"):
        self.openTPSPlan = plan
        self.Gantry = Gantry
        
    def allBeams(self):
        for i,beam in enumerate(self.openTPSPlan.Beams):
            jsonPlan = JsonPlan(self.openTPSPlan, self.Gantry,i)
            jsonPlan.save("beam_" + str(i) + ".json")



class JsonPlan:
    def __init__(self, plan, Gantry = "PPlus", beamID = 0):
        beam = plan.Beams[beamID]
        if Gantry == "PPlus":
            self.bsp = "GTR1-PBS"
            self.sort = "true"
            self.snoutextension = "430"
            self.gantryangle = str(beam.GantryAngle)
            self.rangeshifterid = str(beam.RangeShifterID)
            self.ridgefilterid = ""
            self.rangecompensatorid = ""
            self.blockid = ""
            self.snoutid = ""
            self.actualtemperature = "293.15"
            self.referencetemperature = "293.15"
            self.actualpressure = "1030"
            self.referencepressure = "1030"
            self.dosecorrectionfactor = "1"
            self.ic23offsetx = "0"
            self.ic23offsety = "0"
            self.smoffsetx = "0"
            self.smoffsety = "0" 
            self.ic1positionx = "0"
            self.ic1positiony = "0"
        elif Gantry == "POne":
            self.beamSupplyPointId = "CGTR"
            self.sortSpots = "true"
            self.snoutExtension = "430"
            self.gantryAngle = beam.GantryAngle
            self.beamGatingRequired = "false"
            self.rangeShifterId = str(beam.RangeShifterID)
            self.ridgeFilterId = ""
            self.rangeCompensatorId = ""
            self.blockId = ""
            self.snoutId = ""
            self.actualTemperature = "20.0"
            self.referenceTemperature = "20.0"
            self.actualPressure = "101.325"
            self.referencePressure = "101.325"
            self.doseCorrectionFactor = "1"
            self.icOffsetX = "0"
            self.icOffsetY = "0"
            self.smOffsetX = "0"
            self.smOffsetY = "0" 
            self.ic1PositionX = "0"
            self.ic1PositionY = "0"

        self.mud = "0"
        
        self.beam = self.getLayers(plan,Gantry,beamID)

    def getLayers(self,plan,Gantry,beamID):
        beam = plan.Beams[beamID]
        beamDict = {}
        if Gantry == "PPlus":
            beamDict['mu'] = str(beam.BeamMeterset) 
            beamDict['repaintingtype'] = "None"
            beamDict['layer'] = []
            layerDict = {}
            for layer in beam.Layers:
                layerDict['spottuneid'] = "3.0"
                layerDict['energy'] = str(layer.NominalBeamEnergy)
                layerDict['paintings'] = str(layer.NumberOfPaintings)
                layerDict['spot'] = []
                spotDict = {}
                for s in range(len(layer.SpotMU)):
                    spotDict['x'] = str(layer.ScanSpotPositionMap_x[s])
                    spotDict['y'] = str(layer.ScanSpotPositionMap_y[s])
                    spotDict['metersetweight'] = str(layer.SpotMU[s])
                    #spotDict['metersetweight'] = str(layer.ScanSpotMetersetWeights[s])
                    layerDict['spot'].append(spotDict)
                beamDict['layer'].append(layerDict)
        elif Gantry == "POne":
            beamDict['meterset'] = beam.BeamMeterset
            beamDict['repaintingType'] = "None"
            beamDict['layers'] = []
            layerDict = {}
            for layer in beam.Layers:
                layerDict['spotTuneId'] = "4.0"
                layerDict['nominalBeamEnergy'] = layer.NominalBeamEnergy
                layerDict['numberOfPaintings'] = layer.NumberOfPaintings
                layerDict['spots'] = []
                spotDict = {}
                for s in range(len(layer.SpotMU)):
                    spotDict['positionX'] = layer.ScanSpotPositionMap_x[s]
                    spotDict['positionY'] = layer.ScanSpotPositionMap_y[s]
                    spotDict['metersetWeight'] = layer.SpotMU[s]
                    layerDict['spots'].append(spotDict)
                beamDict['layers'].append(layerDict)
        return beamDict
        
            

    def save(self, file_path):
        with open(file_path, 'w') as fid:
            json.dump(self.__dict__,fid)

    def load(self,file_path):
        with open(file_path) as fid:
            self.data = json.load(fid)
            



