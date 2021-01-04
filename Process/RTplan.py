import pydicom
import numpy as np
import math
import time
import pickle

from Process.SPRimage import *
from Process.OptimizationObjectives import *
from Process.C_libraries.libRayTracing_wrapper import *

class RTplan:

  def __init__(self):
    self.SeriesInstanceUID = ""
    self.SOPInstanceUID = ""
    self.PatientInfo = {}
    self.StudyInfo = {}
    self.DcmFile = ""
    self.Modality = ""
    self.RadiationType = ""
    self.ScanMode = ""
    self.TreatmentMachineName = ""
    self.NumberOfFractionsPlanned = 1
    self.NumberOfSpots = 0
    self.Beams = []
    self.TotalMeterset = 0.0
    self.PlanName = ""
    self.Objectives = OptimizationObjectives()
    self.isLoaded = 0
    self.beamlets = []
    self.OriginalDicomDataset = []
    self.RobustOpti = {"Strategy": "Disabled", "syst_setup": [0.0, 0.0, 0.0], "rand_setup": [0.0, 0.0, 0.0], "syst_range": 0.0}
    self.scenarios = []
    self.NumScenarios = 0
    
    
    
  def print_plan_info(self, prefix=""):
    print(prefix + "Plan: " + self.SeriesInstanceUID)
    print(prefix + "   " + self.DcmFile)
    
    
  
  def import_Dicom_plan(self):
    if(self.isLoaded == 1):
      print("Warning: RTplan " + self.SeriesInstanceUID + " is already loaded")
      return
      
    dcm = pydicom.dcmread(self.DcmFile)

    self.OriginalDicomDataset = dcm
    
    # Photon plan
    if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.5": 
      print("ERROR: Conventional radiotherapy (photon) plans are not supported")
      self.Modality = "Radiotherapy"
      return
  
    # Ion plan  
    elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.8":
      self.Modality = "Ion therapy"
    
      if dcm.IonBeamSequence[0].RadiationType == "PROTON":
        self.RadiationType = "Proton"
      else:
        print("ERROR: Radiation type " + dcm.IonBeamSequence[0].RadiationType + " not supported")
        self.RadiationType = dcm.IonBeamSequence[0].RadiationType
        return
       
      if dcm.IonBeamSequence[0].ScanMode == "MODULATED":
        self.ScanMode = "MODULATED" # PBS
      else:
        print("ERROR: Scan mode " + dcm.IonBeamSequence[0].ScanMode + " not supported")
        self.ScanMode = dcm.IonBeamSequence[0].ScanMode
        return 
    
    # Other  
    else:
      print("ERROR: Unknown SOPClassUID " + dcm.SOPClassUID + " for file " + self.DcmFile)
      self.Modality = "Unknown"
      return
      
    # Start parsing PBS plan
    self.SOPInstanceUID = dcm.SOPInstanceUID
    self.NumberOfFractionsPlanned = int(dcm.FractionGroupSequence[0].NumberOfFractionsPlanned)
    self.NumberOfSpots = 0
    self.TotalMeterset = 0  

    if(hasattr(dcm.IonBeamSequence[0], 'TreatmentMachineName')):
      self.TreatmentMachineName = dcm.IonBeamSequence[0].TreatmentMachineName
    else:
      self.TreatmentMachineName = ""
  
    for dcm_beam in dcm.IonBeamSequence:
      if dcm_beam.TreatmentDeliveryType != "TREATMENT":
        continue
      
      first_layer = dcm_beam.IonControlPointSequence[0]
      
      beam = Plan_IonBeam()
      beam.SeriesInstanceUID = self.SeriesInstanceUID
      beam.BeamName = dcm_beam.BeamName
      beam.IsocenterPosition = [float(first_layer.IsocenterPosition[0]), float(first_layer.IsocenterPosition[1]), float(first_layer.IsocenterPosition[2])]
      beam.GantryAngle = float(first_layer.GantryAngle)
      beam.PatientSupportAngle = float(first_layer.PatientSupportAngle)
      beam.FinalCumulativeMetersetWeight = float(dcm_beam.FinalCumulativeMetersetWeight)
    
      # find corresponding beam in FractionGroupSequence (beam order may be different from IonBeamSequence)
      ReferencedBeam_id = next((x for x, val in enumerate(dcm.FractionGroupSequence[0].ReferencedBeamSequence) if val.ReferencedBeamNumber == dcm_beam.BeamNumber), -1)
      if ReferencedBeam_id == -1:
        print("ERROR: Beam number " + dcm_beam.BeamNumber + " not found in FractionGroupSequence.")
        print("This beam is therefore discarded.")
        continue
      else: beam.BeamMeterset = float(dcm.FractionGroupSequence[0].ReferencedBeamSequence[ReferencedBeam_id].BeamMeterset)
    
      self.TotalMeterset += beam.BeamMeterset
    
      if dcm_beam.NumberOfRangeShifters == 0:
        beam.RangeShifterID = ""
        beam.RangeShifterType = "none"
      elif dcm_beam.NumberOfRangeShifters == 1:
        beam.RangeShifterID = dcm_beam.RangeShifterSequence[0].RangeShifterID
        if dcm_beam.RangeShifterSequence[0].RangeShifterType == "BINARY":
          beam.RangeShifterType = "binary"
        elif dcm_beam.RangeShifterSequence[0].RangeShifterType == "ANALOG":
          beam.RangeShifterType = "analog"
        else:
          print("ERROR: Unknown range shifter type for beam " + dcm_beam.BeamName)
          beam.RangeShifterType = "none"
      else: 
        print("ERROR: More than one range shifter defined for beam " + dcm_beam.BeamName)
        beam.RangeShifterID = ""
        beam.RangeShifterType = "none"
      
      
      SnoutPosition = 0
      if hasattr(first_layer, 'SnoutPosition'):
        SnoutPosition = float(first_layer.SnoutPosition)
    
      IsocenterToRangeShifterDistance = SnoutPosition
      RangeShifterWaterEquivalentThickness = ""
      RangeShifterSetting = "OUT"
      ReferencedRangeShifterNumber = 0
    
      if hasattr(first_layer, 'RangeShifterSettingsSequence'):
        if hasattr(first_layer.RangeShifterSettingsSequence[0], 'IsocenterToRangeShifterDistance'):
          IsocenterToRangeShifterDistance = float(first_layer.RangeShifterSettingsSequence[0].IsocenterToRangeShifterDistance)
        if hasattr(first_layer.RangeShifterSettingsSequence[0], 'RangeShifterWaterEquivalentThickness'):
          RangeShifterWaterEquivalentThickness = float(first_layer.RangeShifterSettingsSequence[0].RangeShifterWaterEquivalentThickness)
        if hasattr(first_layer.RangeShifterSettingsSequence[0], 'RangeShifterSetting'):
          RangeShifterSetting = first_layer.RangeShifterSettingsSequence[0].RangeShifterSetting
        if hasattr(first_layer.RangeShifterSettingsSequence[0], 'ReferencedRangeShifterNumber'):
          ReferencedRangeShifterNumber = int(first_layer.RangeShifterSettingsSequence[0].ReferencedRangeShifterNumber)
       
      CumulativeMeterset = 0
    
      for dcm_layer in dcm_beam.IonControlPointSequence:
        if dcm_layer.NumberOfScanSpotPositions == 1: sum_weights = dcm_layer.ScanSpotMetersetWeights
        else: sum_weights = sum(dcm_layer.ScanSpotMetersetWeights)
      
        if sum_weights == 0.0:
          continue
        
        layer = Plan_IonLayer()
        layer.SeriesInstanceUID = self.SeriesInstanceUID
            
        if hasattr(dcm_layer, 'SnoutPosition'):
          SnoutPosition = float(dcm_layer.SnoutPosition)
        
        if hasattr(dcm_layer, 'NumberOfPaintings'): layer.NumberOfPaintings = int(dcm_layer.NumberOfPaintings)
        else: layer.NumberOfPaintings = 1
       
        layer.NominalBeamEnergy = float(dcm_layer.NominalBeamEnergy)
        layer.ScanSpotPositionMap_x = dcm_layer.ScanSpotPositionMap[0::2]
        layer.ScanSpotPositionMap_y = dcm_layer.ScanSpotPositionMap[1::2]
        layer.ScanSpotMetersetWeights = dcm_layer.ScanSpotMetersetWeights
        layer.SpotMU = np.array(dcm_layer.ScanSpotMetersetWeights) * beam.BeamMeterset / beam.FinalCumulativeMetersetWeight # spot weights are converted to MU
        if layer.SpotMU.size == 1: layer.SpotMU = [layer.SpotMU]
        else: layer.SpotMU = layer.SpotMU.tolist()
      
        self.NumberOfSpots += len(layer.SpotMU)
        CumulativeMeterset += sum(layer.SpotMU)
        layer.CumulativeMeterset = CumulativeMeterset
            
        if beam.RangeShifterType != "none":        
          if hasattr(dcm_layer, 'RangeShifterSettingsSequence'):
            RangeShifterSetting = dcm_layer.RangeShifterSettingsSequence[0].RangeShifterSetting
            ReferencedRangeShifterNumber = dcm_layer.RangeShifterSettingsSequence[0].ReferencedRangeShifterNumber
            if hasattr(dcm_layer.RangeShifterSettingsSequence[0], 'IsocenterToRangeShifterDistance'):
              IsocenterToRangeShifterDistance = dcm_layer.RangeShifterSettingsSequence[0].IsocenterToRangeShifterDistance
            if hasattr(dcm_layer.RangeShifterSettingsSequence[0], 'RangeShifterWaterEquivalentThickness'):
              RangeShifterWaterEquivalentThickness = dcm_layer.RangeShifterSettingsSequence[0].RangeShifterWaterEquivalentThickness
        
          layer.RangeShifterSetting = RangeShifterSetting
          layer.IsocenterToRangeShifterDistance = IsocenterToRangeShifterDistance
          layer.RangeShifterWaterEquivalentThickness = RangeShifterWaterEquivalentThickness
          layer.ReferencedRangeShifterNumber = ReferencedRangeShifterNumber
        
        
        beam.Layers.append(layer)
      
      self.Beams.append(beam)
      
    self.isLoaded = 1
    
    
  
  def Rotate_vector(self, vec, angle, axis):
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
    
    
    
  def compute_cartesian_coordinates(self, CT, Scanner, beams):
    time_start = time.time()
    
    SPR = SPRimage()
    SPR.convert_CT_to_SPR(CT, Scanner)
    
    CTborders_x = [SPR.ImagePositionPatient[0], SPR.ImagePositionPatient[0] + SPR.GridSize[0] * SPR.PixelSpacing[0]]
    CTborders_y = [SPR.ImagePositionPatient[1], SPR.ImagePositionPatient[1] + SPR.GridSize[1] * SPR.PixelSpacing[1]]
    CTborders_z = [SPR.ImagePositionPatient[2], SPR.ImagePositionPatient[2] + SPR.GridSize[2] * SPR.PixelSpacing[2]]
    
    spot_positions = []
    spot_directions = []
    spot_ranges = []

    # initialize spot info for raytracing
    for b in beams:
      beam = self.Beams[b]
      for layer in beam.Layers:

        range_in_water = SPR.energyToRange(layer.NominalBeamEnergy)*10

        for s in range(len(layer.ScanSpotPositionMap_x)):
          
          # BEV coordinates to 3D coordinates: position (x,y,z) and direction (u,v,w)
          x,y,z = layer.ScanSpotPositionMap_x[s], 0, layer.ScanSpotPositionMap_y[s]
          u,v,w = 1e-10, 1.0, 1e-10
          
          # rotation for gantry angle (around Z axis)
          angle = math.radians(beam.GantryAngle)
          [x,y,z] = self.Rotate_vector([x,y,z], angle, 'z')
          [u,v,w] = self.Rotate_vector([u,v,w], angle, 'z')
          
          # rotation for couch angle (around Y axis)
          angle = math.radians(beam.PatientSupportAngle)
          [x,y,z] = self.Rotate_vector([x,y,z], angle, 'y')
          [u,v,w] = self.Rotate_vector([u,v,w], angle, 'y')
          
          # Dicom CT coordinates
          x = x + beam.IsocenterPosition[0]
          y = y + beam.IsocenterPosition[1]
          z = z + beam.IsocenterPosition[2]
          
          # translate initial position at the CT image border
          Translation = np.array([1.0, 1.0, 1.0])
          Translation[0] = (x - CTborders_x[int(u<0)]) / u
          Translation[1] = (y - CTborders_y[int(v<0)]) / v
          Translation[2] = (z - CTborders_z[int(w<0)]) / w
          Translation = Translation.min()
          x = x - Translation * u
          y = y - Translation * v
          z = z - Translation * w

          # append data to the list of spots to process
          spot_positions.append([x,y,z])
          spot_directions.append([u,v,w])
          spot_ranges.append(range_in_water)


    CartesianSpotPositions = compute_position_from_range(SPR, spot_positions, spot_directions, spot_ranges)
          
    print("Spot RayTracing: " + str(time.time()-time_start) + " sec")
    return CartesianSpotPositions


      
  def update_spot_weights(self, new_weights):
    # update weight of initial plan with those from PlanPencil
    count = 0
    self.DeliveredProtons = 0
    self.TotalMeterset = 0
    for beam in self.Beams:
      beam.FinalCumulativeMetersetWeight = 0
      beam.BeamMeterset = 0
      for layer in beam.Layers:
        for s in range(len(layer.SpotMU)):
          layer.ScanSpotMetersetWeights[s] = new_weights[count]
          layer.SpotMU[s] = new_weights[count]
          count += 1

        self.TotalMeterset += sum(layer.SpotMU)
        beam.BeamMeterset += sum(layer.SpotMU)
        beam.FinalCumulativeMetersetWeight += sum(layer.SpotMU)
        layer.CumulativeMeterset = beam.BeamMeterset



  def export_Dicom_with_new_UID(self, OutputFile):
    # generate new uid
    initial_uid = self.OriginalDicomDataset.SOPInstanceUID
    new_uid = pydicom.uid.generate_uid()
    self.OriginalDicomDataset.SOPInstanceUID = new_uid

    # save dicom file
    print("Export dicom RTPLAN: " + OutputFile)
    self.OriginalDicomDataset.save_as(OutputFile)

    # restore initial uid
    self.OriginalDicomDataset.SOPInstanceUID = initial_uid

    return new_uid



  def save(self, file_path):
    beamlets = self.beamlets
    self.beamlets = []
    dcm = self.OriginalDicomDataset
    self.OriginalDicomDataset = []

    with open(file_path, 'wb') as fid:
      pickle.dump(self.__dict__, fid)

    self.beamlets = beamlets
    self.OriginalDicomDataset = dcm



  def load(self, file_path):
    with open(file_path, 'rb') as fid:
      tmp = pickle.load(fid)

    self.__dict__.update(tmp) 
  
    
  
      
class Plan_IonBeam:

  def __init__(self):
    self.SeriesInstanceUID = ""
    self.BeamName = ""
    self.IsocenterPosition = [0,0,0]
    self.GantryAngle = 0.0
    self.PatientSupportAngle = 0.0
    self.FinalCumulativeMetersetWeight = 0.0
    self.BeamMeterset = 0.0
    self.RangeShifterID = ""
    self.RangeShifterType = "none"
    self.Layers = []
    
    
    
class Plan_IonLayer:

  def __init__(self):
    self.SeriesInstanceUID = ""
    self.NumberOfPaintings = 1
    self.NominalBeamEnergy = 0.0
    self.ScanSpotPositionMap_x = []
    self.ScanSpotPositionMap_y = []
    self.ScanSpotMetersetWeights = []
    self.SpotMU = []
    self.CumulativeMeterset = 0.0
    self.RangeShifterSetting = 'OUT'
    self.IsocenterToRangeShifterDistance = 0.0
    self.RangeShifterWaterEquivalentThickness = 0.0
    self.ReferencedRangeShifterNumber = 0
    
    
    
