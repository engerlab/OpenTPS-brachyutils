import os
import numpy as np
import pydicom

from Process.RTplan import *

def export_plan_for_MCsquare(plan, file_path, CT, BDL):

  DestFolder, DestFile = os.path.split(file_path)
  FileName, FileExtension = os.path.splitext(DestFile)
    
  # Convert data for compatibility with MCsquare
  # These transformations may be modified in a future version  
  for beam in plan.Beams:
    beam.MCsquareIsocenter = []
    beam.MCsquareIsocenter.append(beam.IsocenterPosition[0] - CT.ImagePositionPatient[0] + CT.PixelSpacing[0]/2) # change coordinates (origin is now in the corner of the image)
    beam.MCsquareIsocenter.append(beam.IsocenterPosition[1] - CT.ImagePositionPatient[1] + CT.PixelSpacing[1]/2)
    beam.MCsquareIsocenter.append(beam.IsocenterPosition[2] - CT.ImagePositionPatient[2] + CT.PixelSpacing[2]/2)
    beam.MCsquareIsocenter[1] = CT.GridSize[1] * CT.PixelSpacing[1] - beam.MCsquareIsocenter[1] # flip coordinates in Y direction
   
  # Estimate number of delivered protons from MU
  plan.DeliveredProtons = 0
  plan.BeamletRescaling = []
  for beam in plan.Beams:
    for layer in beam.Layers:
      if BDL.isLoaded:
        DeliveredProtons = np.interp(layer.NominalBeamEnergy, BDL.NominalEnergy, BDL.ProtonsMU)
      else:
        DeliveredProtons += BDL.MU_to_NumProtons(1.0, layer.NominalBeamEnergy)
      plan.DeliveredProtons += sum(layer.SpotMU) * DeliveredProtons
      for spot in range(len(layer.SpotMU)):
        plan.BeamletRescaling.append(DeliveredProtons * 1.602176e-19 * 1000)
  
  # export plan      
  print("Write Plan: " + file_path)
  fid = open(file_path,'w');
  fid.write("#TREATMENT-PLAN-DESCRIPTION\n") 
  fid.write("#PlanName\n") 
  fid.write("%s\n" % FileName) 
  fid.write("#NumberOfFractions\n") 
  fid.write("%d\n" % plan.NumberOfFractionsPlanned) 
  fid.write("##FractionID\n") 
  fid.write("1\n")
  fid.write("##NumberOfFields\n") 
  fid.write("%d\n" % len(plan.Beams)) 
  for i in range(len(plan.Beams)):
    fid.write("###FieldsID\n") 
    fid.write("%d\n" % (i+1)) 
  fid.write("#TotalMetersetWeightOfAllFields\n") 
  fid.write("%f\n" % plan.TotalMeterset) 
  
  for i in range(len(plan.Beams)):
    fid.write("\n")
    fid.write("#FIELD-DESCRIPTION\n")
    fid.write("###FieldID\n")
    fid.write("%d\n" % (i+1)) 
    fid.write("###FinalCumulativeMeterSetWeight\n")
    fid.write("%f\n" % plan.Beams[i].BeamMeterset)
    fid.write("###GantryAngle\n")
    fid.write("%f\n" % plan.Beams[i].GantryAngle)
    fid.write("###PatientSupportAngle\n")
    fid.write("%f\n" % plan.Beams[i].PatientSupportAngle)
    fid.write("###IsocenterPosition\n")
    fid.write("%f\t %f\t %f\n" % tuple(plan.Beams[i].MCsquareIsocenter))
    
    if plan.Beams[i].RangeShifterType == "binary":
      RangeShifter = next((RS for RS in BDL.RangeShifters if RS.ID == plan.Beams[i].RangeShifterID), -1)
      if(RangeShifter == -1):
        print("WARNING: Range shifter " + plan.Beams[i].RangeShifterID + " was not found in the BDL.")
      else:
        fid.write("###RangeShifterID\n")
        fid.write("%s\n" % RangeShifter.ID) 
        fid.write("###RangeShifterType\n")
        fid.write("binary\n")
      
    fid.write("###NumberOfControlPoints\n")
    fid.write("%d\n" % len(plan.Beams[i].Layers)) 
    fid.write("\n")
    fid.write("#SPOTS-DESCRIPTION\n")
    
    for j in range(len(plan.Beams[i].Layers)):
      fid.write("####ControlPointIndex\n")
      fid.write("%d\n" % (j+1))
      fid.write("####SpotTunnedID\n")
      fid.write("1\n")
      fid.write("####CumulativeMetersetWeight\n")
      fid.write("%f\n" % plan.Beams[i].Layers[j].CumulativeMeterset)
      fid.write("####Energy (MeV)\n")
      fid.write("%f\n" % plan.Beams[i].Layers[j].NominalBeamEnergy)
      
      if(RangeShifter != -1 and plan.Beams[i].RangeShifterType == "binary"):
        fid.write("####RangeShifterSetting\n")
        fid.write("%s\n" % plan.Beams[i].Layers[j].RangeShifterSetting)
        fid.write("####IsocenterToRangeShifterDistance\n")
        fid.write("%f\n" % plan.Beams[i].Layers[j].IsocenterToRangeShifterDistance)
        fid.write("####RangeShifterWaterEquivalentThickness\n")
        if(plan.Beams[i].Layers[j].RangeShifterWaterEquivalentThickness == ""):
          fid.write("%f\n" % RangeShifter.WET)
        else:
          fid.write("%f\n" % plan.Beams[i].Layers[j].RangeShifterWaterEquivalentThickness)
        
      fid.write("####NbOfScannedSpots\n")
      fid.write("%d\n" % len(plan.Beams[i].Layers[j].SpotMU))
      
      if hasattr(plan.Beams[i].Layers[j], 'SpotTiming'):
        fid.write("####X Y Weight Time\n")
        for k in range(len(plan.Beams[i].Layers[j].SpotMU)):
          fid.write("%f %f %f %f\n" % (plan.Beams[i].Layers[j].ScanSpotPositionMap_x[k], plan.Beams[i].Layers[j].ScanSpotPositionMap_y[k], plan.Beams[i].Layers[j].SpotMU[k], plan.Beams[i].Layers[j].SpotTiming[k]))
      else:
        fid.write("####X Y Weight\n")
        for k in range(len(plan.Beams[i].Layers[j].SpotMU)):
          fid.write("%f %f %f\n" % (plan.Beams[i].Layers[j].ScanSpotPositionMap_x[k], plan.Beams[i].Layers[j].ScanSpotPositionMap_y[k], plan.Beams[i].Layers[j].SpotMU[k]))
      
  fid.close()
  
  
  
def import_MCsquare_plan(file_path, CT):
  DestFolder, DestFile = os.path.split(file_path)
  FileName, FileExtension = os.path.splitext(DestFile)
    
  plan = RTplan()
  plan.SeriesInstanceUID = pydicom.uid.generate_uid()
  plan.PlanName = FileName
  plan.Modality = "Ion therapy"
  plan.RadiationType = "Proton"
  plan.ScanMode = "MODULATED"
  plan.TreatmentMachineName = "Unknown"
  
  NumSpots = 0
  
  with open(file_path, 'r') as f:
    line = f.readline()
    while line:
      # clean the string
      line = line.replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
            
      if line == "#PlanName":
        plan.PlanName = f.readline().replace('\r', '').replace('\n', '').replace('\t', ' ')
        
      elif line == "#NumberOfFractions":
        plan.NumberOfFractionsPlanned = int(f.readline())
      
      elif line == "#TotalMetersetWeightOfAllFields":
        plan.TotalMeterset = float(f.readline())
        
      elif line == "#FIELD-DESCRIPTION":
        plan.Beams.append(Plan_IonBeam())
        plan.Beams[-1].SeriesInstanceUID = plan.SeriesInstanceUID
      
      elif line == "###FieldID" and len(plan.Beams) > 0:
        plan.Beams[-1].BeamName = f.readline()
        
      elif line == "###FinalCumulativeMeterSetWeight":
        plan.Beams[-1].FinalCumulativeMetersetWeight = float(f.readline())
        plan.Beams[-1].BeamMeterset = plan.Beams[-1].FinalCumulativeMetersetWeight
        
      elif line == "###GantryAngle":
        plan.Beams[-1].GantryAngle = float(f.readline())
      
      elif line == "###PatientSupportAngle":
        plan.Beams[-1].PatientSupportAngle = float(f.readline())
        
      elif line == "###IsocenterPosition":
        # read isocenter in MCsquare coordinates
        iso = f.readline().replace('\r', '').replace('\n', '').replace('\t', ' ').split()
        iso = [float(i) for i in iso]
        plan.Beams[-1].MCsquareIsocenter = iso
        
        # convert isocenter in dicom coordinates
        iso[1] = CT.GridSize[1] * CT.PixelSpacing[1] - iso[1]
        iso[0] = iso[0] + CT.ImagePositionPatient[0] - CT.PixelSpacing[0]/2
        iso[1] = iso[1] + CT.ImagePositionPatient[1] - CT.PixelSpacing[1]/2
        iso[2] = iso[2] + CT.ImagePositionPatient[2] - CT.PixelSpacing[2]/2
        plan.Beams[-1].IsocenterPosition = iso
        
      elif line == "####ControlPointIndex":
        plan.Beams[-1].Layers.append(Plan_IonLayer())
        plan.Beams[-1].Layers[-1].SeriesInstanceUID = plan.SeriesInstanceUID
        line = f.readline()
        
      elif line == "####CumulativeMetersetWeight":
        plan.Beams[-1].Layers[-1].CumulativeMeterset = float(f.readline())
        
      elif line == "####Energy(MeV)":
        plan.Beams[-1].Layers[-1].NominalBeamEnergy = float(f.readline())
        
      elif line == "####NbOfScannedSpots":
        NumSpots = int(f.readline())
        plan.NumberOfSpots += NumSpots
        
      elif line == "####XYWeight":
        for s in range(NumSpots):
          data = f.readline().replace('\r', '').replace('\n', '').replace('\t', '').split()
          plan.Beams[-1].Layers[-1].ScanSpotPositionMap_x.append(float(data[0]))
          plan.Beams[-1].Layers[-1].ScanSpotPositionMap_y.append(float(data[1]))
          plan.Beams[-1].Layers[-1].ScanSpotMetersetWeights.append(float(data[2]))
          plan.Beams[-1].Layers[-1].SpotMU.append(float(data[2]))
        
      line = f.readline()
  
  
  #plan.Beams[-1].Layers[-1].RangeShifterSetting = 'OUT'
  #plan.Beams[-1].Layers[-1].IsocenterToRangeShifterDistance = 0.0
  #plan.Beams[-1].Layers[-1].RangeShifterWaterEquivalentThickness = 0.0
  #plan.Beams[-1].Layers[-1].ReferencedRangeShifterNumber = 0
    
  #plan.Beams[-1].RangeShifter = "none"
  #plan.NumberOfSpots = ""
  plan.isLoaded = 1
  
  return plan
  
  
  
def update_weights_from_PlanPencil(file_path, CT, InitialPlan, BDL):
  # read PlanPencil generated by MCsquare
  PlanPencil = import_MCsquare_plan(file_path, CT)
  
  # update weight of initial plan with those from PlanPencil
  InitialPlan.DeliveredProtons = 0
  InitialPlan.TotalMeterset = PlanPencil.TotalMeterset
  for b in range(len(PlanPencil.Beams)):
    InitialPlan.Beams[b].FinalCumulativeMetersetWeight = PlanPencil.Beams[b].FinalCumulativeMetersetWeight
    InitialPlan.Beams[b].BeamMeterset = PlanPencil.Beams[b].BeamMeterset
    for l in range(len(PlanPencil.Beams[b].Layers)):
      InitialPlan.Beams[b].Layers[l].CumulativeMeterset = PlanPencil.Beams[b].Layers[l].CumulativeMeterset
      InitialPlan.Beams[b].Layers[l].ScanSpotMetersetWeights = PlanPencil.Beams[b].Layers[l].ScanSpotMetersetWeights
      InitialPlan.Beams[b].Layers[l].SpotMU = PlanPencil.Beams[b].Layers[l].SpotMU
      if BDL.isLoaded:
        InitialPlan.DeliveredProtons += sum(InitialPlan.Beams[b].Layers[l].SpotMU) * np.interp(InitialPlan.Beams[b].Layers[l].NominalBeamEnergy, BDL.NominalEnergy, BDL.ProtonsMU)
      else:
        InitialPlan.DeliveredProtons += BDL.MU_to_NumProtons(sum(InitialPlan.Beams[b].Layers[l].SpotMU), InitialPlan.Beams[b].Layers[l].NominalBeamEnergy)
  
  
