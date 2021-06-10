import json
from Process.RTplan import *
import requests
import csv

'''
Class to 1) convert openTPS plan into json plan (input for scanAlgo) 
         2) Compute Beam Delivery Time (BDT) based on scanAlgo output

Usage:

from Process.jsonPlan import *

# load OpenTPS plan
file_path = "Plan_OpenTPS.tps"
plan = RTplan()
plan.load(file_path)

# Create BDT object
BDT = BDT(plan)
# Create 1 json file per beam
jsonFiles = BDT.create_jsonFiles()
# call scanAlgo to get times (in ms)
BDT.call_scanAlgo(jsonFiles)
# create inputCSV for arcAlgo
BDT.create_inputCSV("yo.csv")


'''


class BDT:
    def __init__(self,plan, config):
        self.openTPSPlan = plan
        self.params = self.get_config_params(config)
        self.Gantry = self.params['Gantry']
        self.url = self.params['Gateaway']
        self.inputCSV = []

                
    def create_jsonFiles(self):
        jsonFiles = []
        for i,beam in enumerate(self.openTPSPlan.Beams):
            jsonPlan = JsonPlan(self.openTPSPlan, self.Gantry,i)
            filename = "beam_" + str(i) + ".json"
            jsonPlan.save(filename)
            jsonFiles.append(filename)
        return jsonFiles


    def get_config_params(self,config):
        with open(config) as f:
            lines = f.readlines()
            columns = []
            i = 1
            d = {}
            for line in lines:
                if line.strip():
                    line = line.strip().split(',')# remove leading/trailing white spaces
                    key  = line[0].strip()
                    value  = line[1].strip()
                    d[key]=value
        return d


    def call_scanAlgo(self,jsonFilesList):
        previous_energy = 0
        for index,beam in enumerate(jsonFilesList):
            with open(beam,'rb') as f:
                data = json.load(f)
            gantry_angle = data['gantryangle']
            scanAlgo = requests.post(self.url,json=data).json()
            if 'cause' in scanAlgo:
               print("!!!!!!!!! ScanAlgo ERROR in beam !!!!!!! ", index)  
               print('\n')
               print(scanAlgo['cause'])
               print('\n')
            else:
                print('BDT {}  = {} '.format(index,scanAlgo['layer'][-1]['spot'][-1]['start']))
                print('\n')
                angle_time = 300 + (scanAlgo['layer'][-1]['spot'][-1]['start'] + scanAlgo['layer'][-1]['spot'][-1]['duration'] - scanAlgo['layer'][0]['spot'][0]['start'])
                beam_csv = []
                if previous_energy == 0:
                    beam_csv.append(str(gantry_angle))
                    beam_csv.append(str(angle_time))
                    beam_csv.append(str('NA'))
                elif scanAlgo['layer'][0]['energy'] < previous_energy:
                    beam_csv.append(str(gantry_angle))
                    beam_csv.append(str(angle_time))
                    beam_csv.append(str('Down'))
                else:
                    beam_csv.append(str(gantry_angle))
                    beam_csv.append(str(angle_time))
                    beam_csv.append(str('Up'))
                previous_energy = scanAlgo['layer'][-1]['energy']
                self.inputCSV.append(beam_csv)
        
    def create_inputCSV(self,inputCSV_filename):
        header = ['Angle','Time','Switch']
        with open(inputCSV_filename, 'w') as f:
            # create the csv writer
            writer = csv.writer(f)    
            # write the header
            writer.writerow(header)
            writer.writerows(self.inputCSV)
        
    def call_arcAlgo(self, input_CSV_filename, config):
        pass

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
        beam = plan.Beams[beamID]
        beamDict = {}
        if Gantry == "PPlus":
            beamDict['mu'] = str(beam.BeamMeterset) 
            beamDict['repaintingtype'] = "None"
            beamDict['layer'] = []
            for layer in beam.Layers:
                layerDict = {}
                layerDict['spottuneid'] = "3.0"
                layerDict['energy'] = str(layer.NominalBeamEnergy)
                layerDict['paintings'] = str(layer.NumberOfPaintings)
                layerDict['spot'] = []
                for s in range(len(layer.SpotMU)):
                    spotDict = {}
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
            for layer in beam.Layers:
                layerDict = {}
                layerDict['spotTuneId'] = "4.0"
                layerDict['nominalBeamEnergy'] = layer.NominalBeamEnergy
                layerDict['numberOfPaintings'] = layer.NumberOfPaintings
                layerDict['spots'] = []
                for s in range(len(layer.SpotMU)):
                    spotDict = {}
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
            



