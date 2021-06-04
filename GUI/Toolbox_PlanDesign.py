
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDir, pyqtSignal

from GUI.AddBeam_dialog import *
from GUI.AddArc_dialog import *
from GUI.Robustness_Settings_dialog import *

from Process.MCsquare import *
from Process.MCsquare_BDL import *
from Process.PlanOptimization import *


class Toolbox_PlanDesign(QWidget):

  New_plan_created = pyqtSignal(str)

  def __init__(self, PatientList, toolbox_width):
    QWidget.__init__(self)

    self.Patients = PatientList
    self.toolbox_width = toolbox_width
    self.data_path = QDir.currentPath()
    self.CT_disp_ID = -1
    self.Plan_disp_ID = -1
    self.BeamDescription = []
    self.Dose_calculation_param = {"BDL": "", "Scanner": "", "NumProtons": 1e7, "MaxUncertainty": 2.0, "CropContour": "None", "dose2water": True}
    self.RobustOpti = {"Strategy": "Disabled", "syst_setup": [5.0, 5.0, 5.0], "rand_setup": [0.0, 0.0, 0.0], "syst_range": 3.0}

    self.layout = QVBoxLayout()
    self.setLayout(self.layout)
    self.layout.addWidget(QLabel('<b>Plan name:</b>'))
    self.plan_name = QLineEdit('New plan')
    self.layout.addWidget(self.plan_name)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Target:</b>'))
    self.Target = QComboBox()
    self.Target.setMaximumWidth(self.toolbox_width-18)
    self.layout.addWidget(self.Target)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Beams:</b>'))
    self.beams =  QListWidget()
    self.beams.setMaximumHeight(100)
    self.beams.setContextMenuPolicy(Qt.CustomContextMenu)
    self.beams.customContextMenuRequested.connect(lambda pos, list_type='beam': self.List_RightClick(pos, list_type))
    self.layout.addWidget(self.beams)
    self.button_hLoayout = QHBoxLayout()
    self.layout.addLayout(self.button_hLoayout)
    self.addBeam = QPushButton('Add beam')
    self.addBeam.setMaximumWidth(80)
    self.button_hLoayout.addWidget(self.addBeam)
    self.addBeam.clicked.connect(self.add_new_beam) 
    self.addArc = QPushButton('Add arc')
    self.addArc.setMaximumWidth(80)
    self.button_hLoayout.addWidget(self.addArc)
    self.addArc.clicked.connect(self.add_new_arc) 
    self.layout.addSpacing(30)
    self.layout.addWidget(QLabel('<b>Robust optimization:</b>'))
    self.RobustSettings = QLabel('')
    self.layout.addWidget(self.RobustSettings)
    self.layout.addSpacing(10)
    self.RobustnessSettingsButton = QPushButton('Modify robustness settings')
    self.RobustnessSettingsButton.clicked.connect(self.set_robust_opti_settings)
    self.layout.addWidget(self.RobustnessSettingsButton)
    self.layout.addSpacing(30)
    self.CreatePlanButton = QPushButton('Create new plan')
    self.layout.addWidget(self.CreatePlanButton)
    self.CreatePlanButton.clicked.connect(self.create_new_plan) 
    self.layout.addSpacing(15)
    self.ComputeBeamletButton = QPushButton('Compute beamlets')
    self.layout.addWidget(self.ComputeBeamletButton)
    self.ComputeBeamletButton.clicked.connect(self.compute_beamlets) 
    self.layout.addStretch()
    self.LoadPlanButton = QPushButton('Import OpenTPS Plan')
    self.layout.addWidget(self.LoadPlanButton)
    self.LoadPlanButton.clicked.connect(self.import_OpenTPS_Plan) 
    self.layout.addSpacing(10)
    self.LoadMCsquarePlanButton = QPushButton('Import MCsquare PlanPencil')
    self.layout.addWidget(self.LoadMCsquarePlanButton)
    self.LoadMCsquarePlanButton.clicked.connect(self.import_PlanPencil) 
    self.layout.addSpacing(10)
    self.update_robust_opti_settings()
    
  

  def Data_path_changed(self, data_path):
    self.data_path = data_path



  def set_robust_opti_settings(self):
    dialog = Robustness_Settings_dialog(PlanEvaluation=False, RobustParam=self.RobustOpti)
    if(dialog.exec()): self.RobustOpti = dialog.RobustParam
    self.update_robust_opti_settings()



  def Update_dose_calculation_param(self, param):
    self.Dose_calculation_param = param



  def Add_new_contour(self, ROIName):
    self.Target.addItem(ROIName)



  def Remove_contour(self, ID):
    self.Target.removeItem(ID)
    
    
    
  def add_new_beam(self):
    beam_number = self.beams.count()

    # retrieve list of range shifters from BDL
    BDL = MCsquare_BDL()
    BDL.import_BDL(self.Dose_calculation_param["BDL"])
    RangeShifterList = [RS.ID for RS in BDL.RangeShifters]

    dialog = AddBeam_dialog("Beam " + str(beam_number+1), RangeShifterList=RangeShifterList)
    if(dialog.exec()):
      BeamName = dialog.BeamName.text()
      GantryAngle = dialog.GantryAngle.value()
      CouchAngle = dialog.CouchAngle.value()
      RangeShifter = dialog.RangeShifter.currentText()

      if(RangeShifter == "None"): RS_disp=""
      else: RS_disp=", RS"
      self.beams.addItem(BeamName + ":  G=" + str(GantryAngle) + "°,  C=" + str(CouchAngle) + "°" + RS_disp)
      self.BeamDescription.append({"BeamType": "beam", "BeamName": BeamName, "GantryAngle": GantryAngle, "CouchAngle": CouchAngle, "RangeShifter": RangeShifter})
    
    
    
  def add_new_arc(self):
    beam_number = self.beams.count()

    # retrieve list of range shifters from BDL
    BDL = MCsquare_BDL()
    BDL.import_BDL(self.Dose_calculation_param["BDL"])
    RangeShifterList = [RS.ID for RS in BDL.RangeShifters]

    dialog = AddArc_dialog("Arc " + str(beam_number+1), RangeShifterList=RangeShifterList)
    if(dialog.exec()):
      ArcName = dialog.ArcName.text()
      StartGantryAngle = dialog.StartGantryAngle.value()
      StopGantryAngle = dialog.StopGantryAngle.value()
      AngularStep = dialog.AngularStep.value()
      CouchAngle = dialog.CouchAngle.value()
      RangeShifter = dialog.RangeShifter.currentText()

      if(RangeShifter == "None"): RS_disp=""
      else: RS_disp=", RS"
      self.beams.addItem(ArcName + ":  G=" + str(StartGantryAngle) + " to " + str(StopGantryAngle) + "°,  C=" + str(CouchAngle) + "°" + RS_disp)
      self.BeamDescription.append({"BeamType": "arc", "BeamName": ArcName, "StartGantryAngle": StartGantryAngle, "StopGantryAngle": StopGantryAngle, "AngularStep": AngularStep, "CouchAngle": CouchAngle, "RangeShifter": RangeShifter})
  
  
  
  def create_new_plan(self):
    # find selected CT image
    if(self.CT_disp_ID < 0):
      print("Error: No CT image selected")
      return
    patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)
    ct = self.Patients.list[patient_id].CTimages[ct_id]
    
    # target contour
    Target_name = self.Target.currentText()
    patient_id, struct_id, contour_id = self.Patients.find_contour(Target_name)
    Target = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]

    # load BDL
    BDL = MCsquare_BDL()
    BDL.import_BDL(self.Dose_calculation_param["BDL"])
    
    # extract beam info from QListWidget
    BeamNames = []
    GantryAngles = []
    CouchAngles = []
    RangeShifters = []
    AlignLayers = False
    for i in range(self.beams.count()):
      BeamType = self.BeamDescription[i]["BeamType"]
      if(BeamType == "beam"):
        BeamNames.append(self.BeamDescription[i]["BeamName"])
        GantryAngles.append(self.BeamDescription[i]["GantryAngle"])
        CouchAngles.append(self.BeamDescription[i]["CouchAngle"])
        RS_ID = self.BeamDescription[i]["RangeShifter"]
        if(RS_ID == "None"):
          RangeShifter = "None"
        else:
          RangeShifter = next((RS for RS in BDL.RangeShifters if RS.ID == RS_ID), -1)
          if(RangeShifter == -1):
            print("WARNING: Range shifter " + RS_ID + " was not found in the BDL.")
            RangeShifter = "None"
        RangeShifters.append(RangeShifter)

      elif(BeamType == "arc"):
        AlignLayers = True
        name = self.BeamDescription[i]["BeamName"]
        start = self.BeamDescription[i]["StartGantryAngle"]
        stop = self.BeamDescription[i]["StopGantryAngle"]
        step = self.BeamDescription[i]["AngularStep"]
        couch = self.BeamDescription[i]["CouchAngle"]
        RS_ID = self.BeamDescription[i]["RangeShifter"]
        if(RS_ID == "None"):
          RangeShifter = "None"
        else:
          RangeShifter = next((RS for RS in BDL.RangeShifters if RS.ID == RS_ID), -1)
          if(RangeShifter == -1):
            print("WARNING: Range shifter " + RS_ID + " was not found in the BDL.")
            RangeShifter = "None"

        if start > stop:
          start -= 360
        for b in range(math.floor((stop-start)/step)+1):
          angle = start + b * step
          if angle < 0.0: angle += 360
          print(angle)
          BeamNames.append(name + "_" + str(angle))
          GantryAngles.append(angle)
          CouchAngles.append(couch)
          RangeShifters.append(RangeShifter)

    # set spacing parameters
    if(self.RobustOpti["Strategy"] == 'Disabled'): 
      SpotSpacing = 5.0
      LayerSpacing = 5.0
      RTV_margin = max(SpotSpacing, LayerSpacing) * 1.5
    else: 
      SpotSpacing = 5.0
      LayerSpacing = 5.0
      RTV_margin = max(SpotSpacing, LayerSpacing) * 1.5 + max(self.RobustOpti["syst_setup"])

    
    # Generate new plan
    plan = CreatePlanStructure(ct, Target, BeamNames, GantryAngles, CouchAngles, self.Dose_calculation_param["Scanner"], RangeShifters=RangeShifters, RTV_margin=RTV_margin, SpotSpacing=SpotSpacing, LayerSpacing=LayerSpacing, AlignLayersToSpacing=AlignLayers)
    plan.PlanName = self.plan_name.text()
    plan.RobustOpti = self.RobustOpti
    self.Patients.list[patient_id].Plans.append(plan)
    self.New_plan_created.emit(plan.PlanName)
    
    
  
  
  def compute_beamlets(self):
    # find selected CT image
    if(self.CT_disp_ID < 0):
      print("Error: No CT image selected")
      return
    ct_patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)
    ct = self.Patients.list[ct_patient_id].CTimages[ct_id]
    
    # find selected plan
    if(self.Plan_disp_ID < 0):
      print("Error: No treatment plan selected")
      return
    plan_patient_id, plan_id = self.Patients.find_plan(self.Plan_disp_ID)
    plan = self.Patients.list[plan_patient_id].Plans[plan_id]
    
    # configure MCsquare module
    mc2 = MCsquare()
    mc2.BDL.selected_BDL = self.Dose_calculation_param["BDL"]
    mc2.Scanner.selected_Scanner = self.Dose_calculation_param["Scanner"]
    mc2.NumProtons = 5e4
    mc2.dose2water = self.Dose_calculation_param["dose2water"]
    mc2.SetupSystematicError = plan.RobustOpti["syst_setup"]
    mc2.SetupRandomError = plan.RobustOpti["rand_setup"]
    mc2.RangeSystematicError = plan.RobustOpti["syst_range"]
    if(plan.RobustOpti["Strategy"] == 'Disabled'): mc2.Robustness_Strategy = "Disabled"
    else: mc2.Robustness_Strategy = "ErrorSpace_regular"

    # Crop CT image with contour:
    if(self.Dose_calculation_param["CropContour"] == "None"):
      mc2.Crop_CT_contour = {}
    else:
      patient_id, struct_id, contour_id = self.Patients.find_contour(self.Dose_calculation_param["CropContour"])
      mc2.Crop_CT_contour = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
    
    # output folder
    output_path = os.path.join(self.data_path, "OpenTPS")
    if not os.path.isdir(output_path):
      os.mkdir(output_path)

    # run MCsquare simulation
    mc2.MCsquare_beamlet_calculation(ct, plan, output_path)

    # save plan
    plan_file = os.path.join(output_path, "Plan_" + plan.PlanName + "_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S") + ".tps")
    plan.save(plan_file)



  def import_OpenTPS_Plan(self): 
    # find selected CT image
    if(self.CT_disp_ID < 0):
      print("Error: No CT image selected")
      return
    patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)

    # select file
    file_path, _ = QFileDialog.getOpenFileName(self, "Load OpenTPS plan", self.data_path, "OpenTPS data (*.tps);;All files (*.*)")
    if(file_path == ""): return

    # import plan
    plan = RTplan()
    plan.load(file_path)
      
    # add plan to list
    self.Patients.list[patient_id].Plans.append(plan)
    self.New_plan_created.emit(plan.PlanName)
    
  
  
  def import_PlanPencil(self):
    # find selected CT image
    if(self.CT_disp_ID < 0):
      print("Error: No CT image selected")
      return
    patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)
    ct = self.Patients.list[patient_id].CTimages[ct_id]
    
    # select file
    path, _ = QFileDialog.getOpenFileName(self, "Open MCsquare plan", self.data_path, "MCsquare plan (*.txt);;All files (*.*)")
    if(path == ""): return
    
    # import file
    plan = import_MCsquare_plan(path, ct)
    self.Patients.list[patient_id].Plans.append(plan)
    self.New_plan_created.emit(plan.PlanName)



  def update_robust_opti_settings(self):
    if(self.RobustOpti["Strategy"] == 'Disabled'):
      self.RobustSettings.setText('Disabled')
    else:
      RobustSettings = ''
      RobustSettings += 'Selection: error space<br>'
      RobustSettings += 'Syst. setup: E<sub>S</sub> = ' + str(self.RobustOpti["syst_setup"]) + ' mm<br>'
      RobustSettings += 'Rand. setup: &sigma;<sub>S</sub> = ' + str(self.RobustOpti["rand_setup"]) + ' mm<br>'
      RobustSettings += 'Syst. range: E<sub>R</sub> = ' + str(self.RobustOpti["syst_range"]) + ' %'
      self.RobustSettings.setText(RobustSettings)
        
  
  
  def List_RightClick(self, pos, list_type):
    if(list_type == 'beam'):
      item = self.beams.itemAt(pos)
      row = self.beams.row(item)
      pos = self.beams.mapToGlobal(pos)
    
    else: return
    
    if(row > -1):
      self.context_menu = QMenu()
      self.delete_action = QAction("Delete")
      self.delete_action.triggered.connect(lambda checked, list_type=list_type, row=row: self.delete_item(list_type, row))
      self.context_menu.addAction(self.delete_action)
      self.context_menu.popup(pos)
        
        
    
  def delete_item(self, list_type, row):
    if(list_type == 'beam'):
      self.beams.takeItem(row)
      self.BeamDescription.pop(row)
