import json
from opentps.core.data.plan._rtPlan import RTPlan

class ScanAlgoPlan:
    def __init__(self, plan: RTPlan, Gantry = "PPlus", beamID = 0, sort_spots="true"):
        beam = plan._beams[beamID]
        if Gantry == "PPlus":
            self.bsp = "GTR1-PBS"
            self.sort = sort_spots
            self.snoutextension = "430"
            self.gantryangle = str(beam.gantryAngle)
            self.rangeshifterid = str(beam.rangeShifter.ID)
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
            self.sortSpots = sort_spots
            self.snoutExtension = "430"
            self.gantryAngle = beam.gantryAngle
            self.beamGatingRequired = "false"
            self.rangeShifterId = str(beam.rangeShifter.ID)
            self.ridgeFilterId = ""
            self.rangeCompensatorId = ""
            self.blockId = ""
            self.snoutId = ""
            self.actualTemperature = "20.0"
            self.referenceTemperature = "20.0"
            self.actualPressure = "101.325"
#file_path = "data/Phantoms/phantom_3mm/OpenTPS/Plan_phantom_1mm_9Beams_LS5_SS5_RTV7-5_Mai-26-2021_09-48-33.tps"
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
        beam = plan._beams[beamID]
        beamDict = {}
        if Gantry == "PPlus":
            beamDict['mu'] = str(beam.meterset)
            beamDict['repaintingtype'] = "None"
            beamDict['layer'] = []
            for layer in beam._layers:
                layerDict = {}
                layerDict['spottuneid'] = "3.0"
                layerDict['energy'] = str(layer.nominalEnergy)
                layerDict['paintings'] = str(layer.numberOfPaintings)
                layerDict['spot'] = []
                for s in range(len(layer._mu)):
                    spotDict = {}
                    spotDict['x'] = str(layer._x[s])
                    spotDict['y'] = str(layer._y[s])
                    spotDict['metersetweight'] = str(layer._mu[s])
                    #spotDict['metersetweight'] = str(layer.ScanSpotMetersetWeights[s])
                    layerDict['spot'].append(spotDict)
                beamDict['layer'].append(layerDict)
        elif Gantry == "POne":
            beamDict['meterset'] = beam.meterset
            beamDict['repaintingType'] = "None"
            beamDict['layers'] = []
            for layer in beam._layers:
                layerDict = {}
                layerDict['spotTuneId'] = "4.0"
                layerDict['nominalBeamEnergy'] = layer.nominalEnergy
                layerDict['numberOfPaintings'] = layer.numberOfPaintings
                layerDict['spots'] = []
                for s in range(len(layer._mu)):
                    spotDict = {}
                    spotDict['positionX'] = layer._x[s]
                    spotDict['positionY'] = layer._y[s]
                    spotDict['metersetWeight'] = layer._mu[s]
                    layerDict['spots'].append(spotDict)
                beamDict['layers'].append(layerDict)
        return beamDict

    def save(self, file_path):
        with open(file_path, 'w') as fid:
            json.dump(self.__dict__,fid)

    def load(self,file_path):
        with open(file_path) as fid:
            self.data = json.load(fid)