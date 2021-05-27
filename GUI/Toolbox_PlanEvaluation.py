from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDir, pyqtSignal

from GUI.Robustness_Settings_dialog import *

from Process.MCsquare import *
from Process.RobustnessTest import *

class Toolbox_PlanEvaluation(QWidget):

  Robustness_analysis_recomputed = pyqtSignal()

  def __init__(self, PatientList, toolbox_width):
    QWidget.__init__(self)

    self.Patients = PatientList
    self.toolbox_width = toolbox_width
    self.data_path = QDir.currentPath()
    self.CT_disp_ID = -1
    self.Plan_disp_ID = -1
    self.Dose_calculation_param = {"BDL": "", "Scanner": "", "NumProtons": 1e7, "MaxUncertainty": 2.0, "CropContour": "None", "dose2water": True}
    self.RobustEval = {"Strategy": "DoseSpace", "syst_setup": [1.6, 1.6, 1.6], "rand_setup": [1.4, 1.4, 1.4], "syst_range": 1.6}
    self.robustness_scenarios = []

    self.layout = QVBoxLayout()
    self.setLayout(self.layout)
    self.layout.addWidget(QLabel('<b>Scenario selection strategy:</b>'))
    self.Strategy = QLabel('')
    self.layout.addWidget(self.Strategy)
    self.layout.addSpacing(20)
    self.layout.addWidget(QLabel('<b>Scenario errors:</b>'))
    self.Syst_Setup = QLabel('Systematic setup:')
    self.layout.addWidget(self.Syst_Setup)
    self.Rand_Setup = QLabel('Random setup:')
    self.layout.addWidget(self.Rand_Setup)
    self.Syst_Range = QLabel('Systematic range:')
    self.layout.addWidget(self.Syst_Range)
    self.layout.addSpacing(30)
    self.RobustnessSettingsButton = QPushButton('Modify robustness settings')
    self.RobustnessSettingsButton.clicked.connect(self.set_robust_eval_settings)
    self.layout.addWidget(self.RobustnessSettingsButton)
    self.layout.addSpacing(30)
    self.button_hLoayout = QHBoxLayout()
    self.layout.addLayout(self.button_hLoayout)
    self.ComputeScenariosButton = QPushButton('Compute \n Scenarios')
    self.ComputeScenariosButton.setMaximumWidth(100)
    self.button_hLoayout.addWidget(self.ComputeScenariosButton)
    self.ComputeScenariosButton.clicked.connect(self.compute_robustness_scenarios) 
    self.LoadScenariosButton = QPushButton('Load saved \n scenarios')
    self.LoadScenariosButton.setMaximumWidth(100)
    self.button_hLoayout.addWidget(self.LoadScenariosButton)
    self.LoadScenariosButton.clicked.connect(self.load_robustness_scenarios) 
    self.layout.addSpacing(40)
    self.layout.addWidget(QLabel('<b>Displayed dose:</b>'))
    self.DisplayedDose = QComboBox()
    self.DisplayedDose.setMaximumWidth(self.toolbox_width-18)
    self.DisplayedDose.addItems(['Nominal', 'Worst scenario', 'Voxel wise minimum', 'Voxel wise maximum'])
    self.layout.addWidget(self.DisplayedDose)
    self.layout.addSpacing(30)
    self.layout.addWidget(QLabel('<b>Target:</b>'))
    self.Target = QComboBox()
    self.Target.setMaximumWidth(self.toolbox_width-18)
    self.layout.addWidget(self.Target)
    self.layout.addSpacing(10)
    self.layout.addWidget(QLabel('<b>Prescription:</b>'))
    self.Prescription = QDoubleSpinBox()
    self.Prescription.setRange(0.0, 100.0)
    self.Prescription.setSingleStep(1.0)
    self.Prescription.setValue(60.0)
    self.Prescription.setSuffix(" Gy")
    self.layout.addWidget(self.Prescription)
    self.layout.addSpacing(10)
    self.layout.addWidget(QLabel('<b>Evaluation metric:</b>'))
    self.Metric = QComboBox()
    self.Metric.setMaximumWidth(self.toolbox_width-18)
    self.Metric.addItems(['D95', 'MSE'])
    self.layout.addWidget(self.Metric)
    self.layout.addSpacing(10)
    self.CI_label = QLabel('<b>Confidence interval:</b>')
    self.layout.addWidget(self.CI_label)
    self.CI = QSlider(Qt.Horizontal)
    self.CI.setMinimum(0.0)
    self.CI.setMaximum(100.0)
    self.CI.setValue(90.0)
    self.layout.addWidget(self.CI)
    self.layout.addStretch()
    self.CI.valueChanged.connect(self.recompute_robustness_analysis)
    self.Metric.currentIndexChanged.connect(self.recompute_robustness_analysis)
    self.DisplayedDose.currentIndexChanged.connect(self.recompute_robustness_analysis)
    self.Target.currentIndexChanged.connect(self.recompute_robustness_analysis)
    self.Prescription.valueChanged.connect(self.recompute_robustness_analysis)
    self.update_robust_eval_settings()
    self.recompute_robustness_analysis()
    
  

  def Data_path_changed(self, data_path):
    self.data_path = data_path



  def Update_dose_calculation_param(self, param):
    self.Dose_calculation_param = param



  def Add_new_contour(self, ROIName):
    self.Target.addItem(ROIName)



  def Remove_contour(self, ID):
    self.Target.removeItem(ID)



  def set_robust_eval_settings(self):
    dialog = Robustness_Settings_dialog(PlanEvaluation=True, RobustParam=self.RobustEval)
    if(dialog.exec()): self.RobustEval = dialog.RobustParam
    self.update_robust_eval_settings()



  def update_robust_eval_settings(self):
    if(self.RobustEval["Strategy"] == 'ErrorSpace_regular'):
      self.Strategy.setText('Error space (regular)')
      self.Syst_Setup.setText('Syst. setup: E<sub>S</sub> = ' + str(self.RobustEval["syst_setup"]) + ' mm')
      self.Rand_Setup.setText('Rand. setup: &sigma;<sub>S</sub> = ' + str(self.RobustEval["rand_setup"]) + ' mm')
      self.Syst_Range.setText('Syst. range: E<sub>R</sub> = ' + str(self.RobustEval["syst_range"]) + ' %')
    elif(self.RobustEval["Strategy"] == 'ErrorSpace_stat'):
      self.Strategy.setText('Error space (statistical)')
      self.Syst_Setup.setText('Syst. setup: &Sigma;<sub>S</sub> = ' + str(self.RobustEval["syst_setup"]) + ' mm')
      self.Rand_Setup.setText('Rand. setup: &sigma;<sub>S</sub> = ' + str(self.RobustEval["rand_setup"]) + ' mm')
      self.Syst_Range.setText('Syst. range: &Sigma;<sub>R</sub> = ' + str(self.RobustEval["syst_range"]) + ' %')
    else:
      self.Strategy.setText('Dosimetric space (statistical)')
      self.Syst_Setup.setText('Syst. setup: &Sigma;<sub>S</sub> = ' + str(self.RobustEval["syst_setup"]) + ' mm')
      self.Rand_Setup.setText('Rand. setup: &sigma;<sub>S</sub> = ' + str(self.RobustEval["rand_setup"]) + ' mm')
      self.Syst_Range.setText('Syst. range: &Sigma;<sub>R</sub> = ' + str(self.RobustEval["syst_range"]) + ' %')




  def load_robustness_scenarios(self):
    # select folder
    folder_path = QFileDialog.getExistingDirectory(self, "Select robustness test directory", self.data_path)
    if(folder_path == ""): return

    scenarios = RobustnessTest()
    scenarios.load(folder_path)

    if scenarios.SelectionStrategy == "Dosimetric":
      self.RobustEval["Strategy"] = 'DoseSpace'
    else:
      self.RobustEval["Strategy"] = 'ErrorSpace_regular'

    self.RobustEval["syst_setup"] = scenarios.SetupSystematicError
    self.RobustEval["rand_setup"] = scenarios.SetupRandomError
    self.RobustEval["syst_range"] = scenarios.RangeSystematicError

    self.update_robust_eval_settings()
    scenarios.print_info()

    #scenarios.recompute_DVH(self.Patients.list[0].RTstructs[0].Contours)
    #scenarios.save(folder_path)

    self.robustness_scenarios = scenarios
    self.recompute_robustness_analysis()

  
  
  def compute_robustness_scenarios(self):
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

    # find contours
    Target_name = self.Target.currentText()
    patient_id, struct_id, contour_id = self.Patients.find_contour(Target_name)
    AllContours = self.Patients.list[patient_id].RTstructs[struct_id].Contours

    # configure MCsquare module
    mc2 = MCsquare()
    mc2.BDL.selected_BDL = self.Dose_calculation_param["BDL"]
    mc2.Scanner.selected_Scanner = self.Dose_calculation_param["Scanner"]
    mc2.NumProtons = self.Dose_calculation_param["NumProtons"]
    mc2.MaxUncertainty = self.Dose_calculation_param["MaxUncertainty"]
    mc2.dose2water = self.Dose_calculation_param["dose2water"]
    mc2.SetupSystematicError = self.RobustEval["syst_setup"]
    mc2.SetupRandomError = self.RobustEval["rand_setup"]
    mc2.RangeSystematicError = self.RobustEval["syst_range"]
    if(self.RobustEval["Strategy"] == 'DoseSpace'): mc2.Robustness_Strategy = "DoseSpace"
    elif(self.RobustEval["Strategy"] == 'ErrorSpace_stat'): mc2.Robustness_Strategy = "ErrorSpace_stat"
    else: mc2.Robustness_Strategy = "ErrorSpace_regular"

    # Crop CT image with contour:
    if(self.Dose_calculation_param["CropContour"] == "None"):
      mc2.Crop_CT_contour = {}
    else:
      patient_id, struct_id, contour_id = self.Patients.find_contour(self.Dose_calculation_param["CropContour"])
      mc2.Crop_CT_contour = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]

    # run MCsquare simulation
    scenarios = mc2.MCsquare_RobustScenario_calculation(ct, plan, AllContours)

    # save data
    output_path = os.path.join(self.data_path, "OpenTPS")
    if not os.path.isdir(output_path):
      os.mkdir(output_path)
    output_folder = os.path.join(output_path, "RobustnessTest_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S"))
    scenarios.save(output_folder)

    self.robustness_scenarios = scenarios
    self.recompute_robustness_analysis()



  def recompute_robustness_analysis(self):

    if(self.robustness_scenarios == []): return

    CI = self.CI.value()
    self.CI_label.setText('<b>Confidence interval:</b> &nbsp;&nbsp;&nbsp; ' + str(CI) + " %")

    # target contour
    Target_name = self.Target.currentText()
    if(Target_name == ''): return
    patient_id, struct_id, contour_id = self.Patients.find_contour(Target_name)
    Target = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
    TargetPrescription = self.Prescription.value()

    self.robustness_scenarios.DoseDistributionType = self.DisplayedDose.currentText()

    if(self.robustness_scenarios.SelectionStrategy == "Dosimetric"):
      self.robustness_scenarios.dosimetric_space_analysis(self.Metric.currentText(), CI, Target, TargetPrescription)
    else:
      self.robustness_scenarios.error_space_analysis(self.Metric.currentText(), Target, TargetPrescription)

    self.Robustness_analysis_recomputed.emit()