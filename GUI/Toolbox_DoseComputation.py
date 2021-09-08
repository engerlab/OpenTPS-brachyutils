
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal

from Process.MCsquare import *
from Process.RTdose import *
from Process.DeepLearning_denoising.Denoise_MC_dose import *


class Toolbox_DoseComputation(QWidget):

  New_dose_created = pyqtSignal(str)
  Dose_calculation_param_changed = pyqtSignal(dict)
  Run_plan_optimization = pyqtSignal()

  def __init__(self, PatientList, toolbox_width):
    QWidget.__init__(self)

    self.Patients = PatientList
    self.toolbox_width = toolbox_width
    self.CT_disp_ID = -1
    self.Plan_disp_ID = -1
    self.Dose_calculation_param = {"BDL": "", "Scanner": "", "NumProtons": 1e7, "MaxUncertainty": 2.0, "CropContour": "None", "dose2water": True}

    mc2 = MCsquare()

    self.layout = QVBoxLayout()
    self.setLayout(self.layout)
    self.layout.addWidget(QLabel('<b>Dose name:</b>'))
    self.dose_name = QLineEdit('MCsquare_dose')
    self.layout.addWidget(self.dose_name)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Beam model:</b>'))
    self.BDL_List = QComboBox()
    self.BDL_List.setMaximumWidth(self.toolbox_width-18)
    self.BDL_List.addItems(mc2.BDL.list)
    self.BDL_List.currentIndexChanged.connect(self.Update_dose_calculation_param)
    self.layout.addWidget(self.BDL_List)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Scanner calibration:</b>'))
    self.Scanner_List = QComboBox()
    self.Scanner_List.setMaximumWidth(self.toolbox_width-18)
    self.Scanner_List.addItems(mc2.Scanner.list)
    self.Scanner_List.currentIndexChanged.connect(self.Update_dose_calculation_param)
    self.layout.addWidget(self.Scanner_List)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Simulation statistics:</b>'))
    self.NumProtons = QSpinBox()
    self.NumProtons.setGroupSeparatorShown(True)
    self.NumProtons.setRange(0, 1e9)
    self.NumProtons.setSingleStep(1e6)
    self.NumProtons.setValue(1e7)
    self.NumProtons.setSuffix(" protons")
    self.NumProtons.valueChanged.connect(self.Update_dose_calculation_param)
    self.layout.addWidget(self.NumProtons)
    self.MaxUncertainty = QDoubleSpinBox()
    self.MaxUncertainty.setGroupSeparatorShown(True)
    self.MaxUncertainty.setRange(0.0, 100.0)
    self.MaxUncertainty.setSingleStep(0.1)
    self.MaxUncertainty.setValue(2.0)
    self.MaxUncertainty.setSuffix("% uncertainty")
    self.MaxUncertainty.valueChanged.connect(self.Update_dose_calculation_param)
    self.layout.addWidget(self.MaxUncertainty)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Crop CT with contour:</b>'))
    self.CropContour = QComboBox()
    self.CropContour.setMaximumWidth(self.toolbox_width-18)
    self.CropContour.addItem("None")
    self.CropContour.currentIndexChanged.connect(self.Update_dose_calculation_param)
    self.layout.addWidget(self.CropContour)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Other parameters:</b>'))
    self.dose2water = QCheckBox('convert dose-to-water')
    self.dose2water.setChecked(True)
    self.dose2water.stateChanged.connect(self.Update_dose_calculation_param)
    self.layout.addWidget(self.dose2water)
    self.DoseDenoising = QCheckBox('denoising (Deep Learning)')
    self.DoseDenoising.setChecked(False)
    self.layout.addWidget(self.DoseDenoising)
    self.layout.addSpacing(30)
    self.RunButton = QPushButton('Run dose calculation')
    self.layout.addWidget(self.RunButton)
    self.RunButton.clicked.connect(self.run_MCsquare) 
    self.layout.addSpacing(30)
    self.ComputeBeamletButton = QPushButton('Compute beamlets')
    self.layout.addWidget(self.ComputeBeamletButton)
    self.ComputeBeamletButton.clicked.connect(self.compute_beamlets) 
    self.layout.addStretch()
    
    



  def Add_new_contour(self, ROIName):
    self.CropContour.addItem(ROIName)



  def Remove_contour(self, ID):
    self.CropContour.removeItem(ID+1)
    
  

  def Data_path_changed(self, data_path):
    self.data_path = data_path



  def Update_dose_calculation_param(self):
    self.Dose_calculation_param["BDL"] = self.BDL_List.currentText()
    self.Dose_calculation_param["Scanner"] = self.Scanner_List.currentText()
    self.Dose_calculation_param["NumProtons"] = self.NumProtons.value()
    self.Dose_calculation_param["MaxUncertainty"] = self.MaxUncertainty.value()
    self.Dose_calculation_param["CropContour"] = self.CropContour.currentText()
    self.Dose_calculation_param["dose2water"] = self.dose2water.checkState()
    self.Dose_calculation_param_changed.emit(self.Dose_calculation_param)



  def run_MCsquare(self):
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
    mc2.DoseName = self.dose_name.text()
    mc2.BDL.selected_BDL = self.BDL_List.currentText()
    mc2.Scanner.selected_Scanner = self.Scanner_List.currentText()
    mc2.NumProtons = self.NumProtons.value()
    mc2.MaxUncertainty = self.MaxUncertainty.value()
    mc2.dose2water = self.dose2water.checkState()

    # Crop CT image with contour:
    if(self.CropContour.currentIndex() > 0):
      patient_id, struct_id, contour_id = self.Patients.find_contour(self.CropContour.currentText())
      mc2.Crop_CT_contour = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
    
    # run MCsquare simulation
    mhd_dose = mc2.MCsquare_simulation(ct, plan)
    
    # load dose image in the database
    dose = RTdose().Initialize_from_MHD(mc2.DoseName, mhd_dose, ct, plan)
    self.Patients.list[plan_patient_id].RTdoses.append(dose)
    self.New_dose_created.emit(dose.ImgName)
    
    # deep learning dose denoising
    if(self.DoseDenoising.checkState()):
      DenoisedDose = RTdose().Initialize_from_MHD(mc2.DoseName + "_denoised", mhd_dose, ct, plan)
      DenoisedDose.Image = Denoise_MC_dose(dose.Image, 'dUNet_24')
      self.Patients.list[plan_patient_id].RTdoses.append(DenoisedDose)
      self.New_dose_created.emit(DenoisedDose.ImgName)
    
    
  
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
    mc2.BDL.selected_BDL = self.BDL_List.currentText()
    mc2.Scanner.selected_Scanner = self.Scanner_List.currentText()
    mc2.NumProtons = 5e4
    mc2.dose2water = self.dose2water.checkState()
    mc2.SetupSystematicError = plan.RobustOpti["syst_setup"]
    mc2.SetupRandomError = plan.RobustOpti["rand_setup"]
    mc2.RangeSystematicError = plan.RobustOpti["syst_range"]
    if(plan.RobustOpti["Strategy"] == 'Disabled'): mc2.Robustness_Strategy = "Disabled"
    else: mc2.Robustness_Strategy = "ErrorSpace_regular"

    # Crop CT image with contour:
    if(self.CropContour.currentIndex() > 0):
      patient_id, struct_id, contour_id = self.Patients.find_contour(self.Dose_calculation_param["CropContour"])
      mc2.Crop_CT_contour = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
    else: mc2.Crop_CT_contour = {}
    
    # output folder
    output_path = os.path.join(self.data_path, "OpenTPS")
    if not os.path.isdir(output_path):
      os.mkdir(output_path)

    # run MCsquare simulation
    mc2.MCsquare_beamlet_calculation(ct, plan, output_path)

    # save plan with beamlets
    plan_file = os.path.join(output_path, "Plan_" + plan.PlanName + "_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S") + ".tps")
    plan.save(plan_file)



  def compute_beamlets_SLOT(self):
    self.compute_beamlets()
    self.Run_plan_optimization.emit()