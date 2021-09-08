from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDir, pyqtSignal

from GUI.AddObjective_dialog import *
from GUI.ObjectiveTemplateWindow import *

from Process.MCsquare import *
from Process.PlanOptimization import *


class Toolbox_PlanOptimization(QWidget):

  New_dose_created = pyqtSignal(str)
  Run_beamlet_calculation = pyqtSignal()

  def __init__(self, PatientList, toolbox_width):
    QWidget.__init__(self)

    self.Patients = PatientList
    self.toolbox_width = toolbox_width
    self.data_path = QDir.currentPath()
    self.CT_disp_ID = -1
    self.Plan_disp_ID = -1
    self.Dose_calculation_param = {"BDL": "", "Scanner": "", "NumProtons": 1e7, "MaxUncertainty": 2.0, "CropContour": "None", "dose2water": True}

    self.layout = QVBoxLayout()
    self.setLayout(self.layout)
    self.layout.addWidget(QLabel('<b>Optimization algorithm:</b>'))
    self.Algorithm = QComboBox()
    self.Algorithm.addItem("Beamlet-free MCsquare")
    self.Algorithm.addItem("Beamlet-based BFGS")
    self.Algorithm.addItem("Beamlet-based L-BFGS")
    self.Algorithm.addItem("Beamlet-based Scipy-lBFGS")
    self.Algorithm.setMaximumWidth(self.toolbox_width-18)
    self.layout.addWidget(self.Algorithm)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Target:</b>'))
    self.Target = QComboBox()
    self.Target.setMaximumWidth(self.toolbox_width-18)
    self.layout.addWidget(self.Target)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Prescription:</b>'))
    self.Prescription = QDoubleSpinBox()
    self.Prescription.setRange(0.0, 100.0)
    self.Prescription.setSingleStep(1.0)
    self.Prescription.setValue(60.0)
    self.Prescription.setSuffix(" Gy")
    self.layout.addWidget(self.Prescription)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Objectives:</b>'))
    self.objectives =  QListWidget()
    self.objectives.setSpacing(2)
    self.objectives.setAlternatingRowColors(True)
    self.objectives.setMaximumHeight(150)
    self.objectives.setContextMenuPolicy(Qt.CustomContextMenu)
    self.objectives.customContextMenuRequested.connect(lambda pos, list_type='objective': self.List_RightClick(pos, list_type))
    self.layout.addWidget(self.objectives)
    self.button_hLoayout = QHBoxLayout()
    self.layout.addLayout(self.button_hLoayout)
    self.addObjective = QPushButton('Add objective')
    self.addObjective.setMaximumWidth(100)
    self.button_hLoayout.addWidget(self.addObjective)
    self.addObjective.clicked.connect(self.add_new_objective) 
    self.TemplateBtn = QPushButton('Templates')
    self.TemplateBtn.setMaximumWidth(100)
    self.button_hLoayout.addWidget(self.TemplateBtn)
    self.TemplateBtn.clicked.connect(self.TemplateWindow) 
    self.layout.addSpacing(30)
    self.OptimizePlanButton = QPushButton('Optimize plan')
    self.layout.addWidget(self.OptimizePlanButton)
    self.OptimizePlanButton.clicked.connect(self.optimize_plan) 
    self.layout.addStretch()
    
  

  def Data_path_changed(self, data_path):
    self.data_path = data_path



  def Update_dose_calculation_param(self, param):
    self.Dose_calculation_param = param



  def Add_new_contour(self, ROIName):
    self.Target.addItem(ROIName)



  def Remove_contour(self, ID):
    self.Target.removeItem(ID)



  def add_new_objective(self):
    # get list of contours
    ContourList = []
    for i in range(self.Target.count()):
      ContourList.append(self.Target.itemText(i))

    # find selected plan
    if(self.Plan_disp_ID < 0):
      print("Error: No treatment plan selected")
      return
    plan_patient_id, plan_id = self.Patients.find_plan(self.Plan_disp_ID)
    plan = self.Patients.list[plan_patient_id].Plans[plan_id]
    
    # create dialog window
    if(plan.RobustOpti["Strategy"] == 'Disabled'): dialog = AddObjective_dialog(ContourList, RobustOpti=False)
    else: dialog = AddObjective_dialog(ContourList, RobustOpti=True)

    obj_number = self.objectives.count()
    if(obj_number == 0): dialog.Contour.setCurrentText(self.Target.currentText())
    else: dialog.Contour.setCurrentText(self.objectives.item(obj_number-1).data(Qt.UserRole+0))
    
    # get objective inputs
    if(dialog.exec()):
      ROIName = dialog.Contour.currentText()
      Metric = dialog.Metric.currentText()
      Condition = dialog.Condition.currentText()
      LimitValue = dialog.LimitValue.value()
      Weight = dialog.Weight.value()
      Robust = dialog.Robust.isChecked()
      if(Robust == True):
        self.objectives.addItem(ROIName + ":\n" + Metric + " " + Condition + " " + str(LimitValue) + " Gy   (w=" + str(Weight) + ", robust)")
      else:
        self.objectives.addItem(ROIName + ":\n" + Metric + " " + Condition + " " + str(LimitValue) + " Gy   (w=" + str(Weight) + ")")
      self.objectives.item(obj_number).setData(Qt.UserRole+0, ROIName)
      self.objectives.item(obj_number).setData(Qt.UserRole+1, Metric)
      self.objectives.item(obj_number).setData(Qt.UserRole+2, Condition)
      self.objectives.item(obj_number).setData(Qt.UserRole+3, LimitValue)
      self.objectives.item(obj_number).setData(Qt.UserRole+4, Weight)
      self.objectives.item(obj_number).setData(Qt.UserRole+5, Robust)

  
  
  def TemplateWindow(self):
    # get list of contours
    ContourList = []
    for i in range(self.Target.count()):
      ContourList.append(self.Target.itemText(i))

    # get saved templates
    Templates = ObjectiveTemplateList()
    
    # create dialog window
    dialog = ObjectiveTemplateWindow(ContourList, Templates)
    
    # get template
    if(dialog.exec()):
      for objective in Templates.list[Templates.SelectedID].Objectives:
        if objective.ROIName in ContourList:
          obj_number = self.objectives.count()
          self.objectives.addItem(objective.ROIName + ":\n" + objective.Metric + " " + objective.Condition + " " + str(objective.LimitValue) + " Gy   (w=" + str(objective.Weight) + ")")
          self.objectives.item(obj_number).setData(Qt.UserRole+0, objective.ROIName)
          self.objectives.item(obj_number).setData(Qt.UserRole+1, objective.Metric)
          self.objectives.item(obj_number).setData(Qt.UserRole+2, objective.Condition)
          self.objectives.item(obj_number).setData(Qt.UserRole+3, objective.LimitValue)
          self.objectives.item(obj_number).setData(Qt.UserRole+4, objective.Weight)
          self.objectives.item(obj_number).setData(Qt.UserRole+5, objective.Robust)

      
    
  def optimize_plan(self):
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
    
    # encode optimization objectives
    Target = self.Target.currentText()
    ROINames = set([Target])
    Prescription = self.Prescription.value()
    plan.Objectives.setTarget(Target, Prescription)
    plan.Objectives.list = []
    for i in range(self.objectives.count()):
      ROIName = self.objectives.item(i).data(Qt.UserRole+0)
      Metric = self.objectives.item(i).data(Qt.UserRole+1)
      Condition = self.objectives.item(i).data(Qt.UserRole+2)
      LimitValue = self.objectives.item(i).data(Qt.UserRole+3)
      Weight = self.objectives.item(i).data(Qt.UserRole+4)
      Robust = self.objectives.item(i).data(Qt.UserRole+5)
      plan.Objectives.addObjective(ROIName, Metric, Condition, LimitValue, Weight, Robust=Robust)
      ROINames.add(ROIName)
      
    # create list of contours
    contours = []
    for ROI in ROINames:
      patient_id, struct_id, contour_id = self.Patients.find_contour(ROI)
      contours.append(self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id])

    # Beamlet-free optimization algorithm
    if(self.Algorithm.currentText() == "Beamlet-free MCsquare"):
      # configure MCsquare module
      mc2 = MCsquare()
      mc2.DoseName = plan.PlanName
      mc2.BDL.selected_BDL = self.Dose_calculation_param["BDL"]
      mc2.Scanner.selected_Scanner = self.Dose_calculation_param["Scanner"]
      mc2.NumProtons = self.Dose_calculation_param["NumProtons"]
      mc2.dose2water = self.Dose_calculation_param["dose2water"]
      mc2.PlanOptimization = "beamlet-free"


      # Crop CT image with contour:
      if(self.Dose_calculation_param["CropContour"] == "None"):
        mc2.Crop_CT_contour = {}
      else:
        patient_id, struct_id, contour_id = self.Patients.find_contour(self.Dose_calculation_param["CropContour"])
        mc2.Crop_CT_contour = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
          
      # run MCsquare optimization
      mhd_dose = mc2.BeamletFree_optimization(ct, plan, contours)
      dose = RTdose().Initialize_from_MHD(mc2.DoseName, mhd_dose, ct, plan)


    # Beamlet-based optimization methods
    else:
      # check beamlets
      if(plan.beamlets == []):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText("Beamlet were not computed for this treatment plan.")
        msg_box.setInformativeText("Do you want to pre-compute " + str(plan.NumberOfSpots) + " beamlets now?")
        msg_box.setWindowTitle("Beamlet calculation")
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        answer = msg_box.exec()
        if(answer == QMessageBox.Ok):
          self.Run_beamlet_calculation.emit()
          return
        else:
          print("Error: beamlets must be pre-computed")
          return

      # beamlet-based optimization with BFGS
      if(self.Algorithm.currentText() == "Beamlet-based BFGS"):
        w, dose_vector, ps = OptimizeWeights(plan, contours, method="BFGS")

      # beamlet-based optimization with L-BFGS
      elif(self.Algorithm.currentText() == "Beamlet-based L-BFGS"):
        w, dose_vector, ps = OptimizeWeights(plan, contours, method="L-BFGS")

      # beamlet-based optimization with FISTA
      elif(self.Algorithm.currentText() == "Beamlet-based Scipy-lBFGS"):
        w, dose_vector, ps = OptimizeWeights(plan, contours, method="Scipy-lBFGS")

      dose = RTdose().Initialize_from_beamlet_dose(plan.PlanName, plan.beamlets, dose_vector, ct)

    # add dose image in the database
    self.Patients.list[plan_patient_id].RTdoses.append(dose)
    self.New_dose_created.emit(dose.ImgName)

    # save plan
    output_path = os.path.join(self.data_path, "OpenTPS")
    if not os.path.isdir(output_path):
      os.mkdir(output_path)
    plan_file = os.path.join(output_path, "Plan_" + plan.PlanName + "_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S") + ".tps")
    plan.save(plan_file)
        
        
    
  def delete_item(self, list_type, row):
    if(list_type == 'objective'):
      self.objectives.takeItem(row)
        
  
  
  def List_RightClick(self, pos, list_type):
    if(list_type == 'objective'):
      item = self.objectives.itemAt(pos)
      row = self.objectives.row(item)
      pos = self.objectives.mapToGlobal(pos)
    
    else: return
    
    if(row > -1):
      self.context_menu = QMenu()
      self.delete_action = QAction("Delete")
      self.delete_action.triggered.connect(lambda checked, list_type=list_type, row=row: self.delete_item(list_type, row))
      self.context_menu.addAction(self.delete_action)
      self.context_menu.popup(pos)