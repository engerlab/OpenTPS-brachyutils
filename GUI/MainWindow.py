from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QIcon, QPalette, QPen
from PyQt5.QtCore import Qt, QDir, QPointF
import pyqtgraph as qtg
import numpy as np
import datetime

from GUI.AddBeam_dialog import *
from GUI.AddArc_dialog import *
from GUI.AddObjective_dialog import *
from GUI.Robustness_Settings_dialog import *
from GUI.ObjectiveTemplateWindow import *

from Process.PatientData import *
from Process.RTdose import *
from Process.RTplan import *
from Process.DVH import *
from Process.MCsquare import *
from Process.MCsquare_plan import *
from Process.MCsquare_sparse_format import *
from Process.PlanOptimization import *
from Process.DeepLearning_denoising.Denoise_MC_dose import *

class MainWindow(QMainWindow):
  def __init__(self):
    # initialize data
    self.Patients = PatientList()
    self.data_path = QDir.currentPath()
    self.ROI_CheckBox = []
    self.Viewer_initialized = 0
    self.Viewer_CT = np.array([])
    self.Viewer_Dose = np.array([])
    self.Viewer_Contours = np.array([])
    self.Viewer_IsoCenter = []
    self.Viewer_Spots = []
    self.Viewer_axial_slice = 0
    self.Viewer_coronal_slice = 0
    self.Viewer_sagittal_slice = 0
    self.Viewer_resolution = [1,1,1]
    self.RobustEval = {"Strategy": "DoseSpace", "syst_setup": [1.6, 1.6, 1.6], "rand_setup": [1.4, 1.4, 1.4], "syst_range": 1.6}
    self.RobustOpti = {"Strategy": "Disabled", "syst_setup": [5.0, 5.0, 5.0], "rand_setup": [0.0, 0.0, 0.0], "syst_range": 3.0}
    self.robustness_scenarios = []
  
    # initialize the main window
    QMainWindow.__init__(self)
    self.setWindowTitle('OpenTPS')
    self.resize(1400, 900)
    self.main_layout = QHBoxLayout()
    self.central_Widget = QWidget()
    self.central_Widget.setLayout(self.main_layout)
    self.setCentralWidget(self.central_Widget)
    self.setWindowIcon(QIcon('GUI' + os.path.sep + 'res' + os.path.sep + 'icon.png'))
    
    # initialize the toolbox
    self.toolbox_width = 270
    self.toolbox_main = QToolBox()
    self.toolbox_main.setStyleSheet("QToolBox::tab {font: bold; color: #000000; font-size: 16px;}")
    self.main_layout.addWidget(self.toolbox_main)
    self.toolbox_main.setFixedWidth(self.toolbox_width)
    self.toolbox_main.currentChanged.connect(self.menu_changed)
    self.toolbox_main.previous_index = 0
    
    # initialize the 1st toolbox panel (patient data)
    self.toolbox_1 = QWidget()
    self.toolbox_main.addItem(self.toolbox_1, 'Patient data')
    self.toolbox_1_layout = QVBoxLayout()
    self.toolbox_1.setLayout(self.toolbox_1_layout)
    self.toolbox_1_layout.addWidget(QLabel('<b>CT images:</b>'))
    self.toolbox_1_CT_list = QListWidget()
    self.toolbox_1_CT_list.currentRowChanged.connect(self.Current_CT_changed) 
    self.toolbox_1_CT_list.setContextMenuPolicy(Qt.CustomContextMenu)
    self.toolbox_1_CT_list.customContextMenuRequested.connect(lambda pos, list_type='CT': self.List_RightClick(pos, list_type))
    self.toolbox_1_layout.addWidget(self.toolbox_1_CT_list)
    self.toolbox_1_layout.addSpacing(10)
    self.toolbox_1_layout.addWidget(QLabel('<b>Dose distributions:</b>'))
    self.toolbox_1_Dose_list = QListWidget()
    self.toolbox_1_Dose_list.currentRowChanged.connect(self.Current_dose_changed) 
    self.toolbox_1_Dose_list.setContextMenuPolicy(Qt.CustomContextMenu)
    self.toolbox_1_Dose_list.customContextMenuRequested.connect(lambda pos, list_type='dose': self.List_RightClick(pos, list_type))
    self.toolbox_1_layout.addWidget(self.toolbox_1_Dose_list)
    self.toolbox_1_layout.addSpacing(10)
    self.toolbox_1_layout.addWidget(QLabel('<b>Treatment plans:</b>'))
    self.toolbox_1_Plan_list = QListWidget()
    self.toolbox_1_Plan_list.setContextMenuPolicy(Qt.CustomContextMenu)
    self.toolbox_1_Plan_list.customContextMenuRequested.connect(lambda pos, list_type='plan': self.List_RightClick(pos, list_type))
    self.toolbox_1_layout.addWidget(self.toolbox_1_Plan_list)
    self.toolbox_1_layout.addSpacing(10)
    self.toolbox_1_LoadButton = QPushButton('Load patient data')
    self.toolbox_1_layout.addWidget(self.toolbox_1_LoadButton)
    self.toolbox_1_LoadButton.clicked.connect(self.load_patient_data) 
    
    # initialize the 2nd toolbox panel (ROI)
    self.toolbox_2 = QWidget()
    self.toolbox_main.addItem(self.toolbox_2, 'ROI')
    self.toolbox_2_layout = QVBoxLayout()
    self.toolbox_2.setLayout(self.toolbox_2_layout)
    self.toolbox_2_layout.addWidget(QLabel("No ROI loaded"))
    
    # initialize the 3rd toolbox panel (Dose computation)
    mc2 = MCsquare()
    self.toolbox_3 = QWidget()
    self.toolbox_main.addItem(self.toolbox_3, 'Dose computation')
    self.toolbox_3_layout = QVBoxLayout()
    self.toolbox_3.setLayout(self.toolbox_3_layout)
    self.toolbox_3_layout.addWidget(QLabel('<b>Dose name:</b>'))
    self.toolbox_3_dose_name = QLineEdit('MCsquare_dose')
    self.toolbox_3_layout.addWidget(self.toolbox_3_dose_name)
    self.toolbox_3_layout.addSpacing(15)
    self.toolbox_3_layout.addWidget(QLabel('<b>Beam model:</b>'))
    self.toolbox_3_BDL_List = QComboBox()
    self.toolbox_3_BDL_List.setMaximumWidth(self.toolbox_width-18)
    self.toolbox_3_BDL_List.addItems(mc2.BDL.list)
    self.toolbox_3_layout.addWidget(self.toolbox_3_BDL_List)
    self.toolbox_3_layout.addSpacing(15)
    self.toolbox_3_layout.addWidget(QLabel('<b>Scanner calibration:</b>'))
    self.toolbox_3_Scanner_List = QComboBox()
    self.toolbox_3_Scanner_List.setMaximumWidth(self.toolbox_width-18)
    self.toolbox_3_Scanner_List.addItems(mc2.Scanner.list)
    self.toolbox_3_layout.addWidget(self.toolbox_3_Scanner_List)
    self.toolbox_3_layout.addSpacing(15)
    self.toolbox_3_layout.addWidget(QLabel('<b>Simulation statistics:</b>'))
    self.toolbox_3_NumProtons = QSpinBox()
    self.toolbox_3_NumProtons.setGroupSeparatorShown(True)
    self.toolbox_3_NumProtons.setRange(0, 1e9)
    self.toolbox_3_NumProtons.setSingleStep(1e6)
    self.toolbox_3_NumProtons.setValue(1e7)
    self.toolbox_3_NumProtons.setSuffix(" protons")
    self.toolbox_3_layout.addWidget(self.toolbox_3_NumProtons)
    self.toolbox_3_MaxUncertainty = QDoubleSpinBox()
    self.toolbox_3_MaxUncertainty.setGroupSeparatorShown(True)
    self.toolbox_3_MaxUncertainty.setRange(0.0, 100.0)
    self.toolbox_3_MaxUncertainty.setSingleStep(0.1)
    self.toolbox_3_MaxUncertainty.setValue(2.0)
    self.toolbox_3_MaxUncertainty.setSuffix("% uncertainty")
    self.toolbox_3_layout.addWidget(self.toolbox_3_MaxUncertainty)
    self.toolbox_3_layout.addSpacing(15)
    self.toolbox_3_layout.addWidget(QLabel('<b>Crop CT with contour:</b>'))
    self.toolbox_3_CropContour = QComboBox()
    self.toolbox_3_CropContour.setMaximumWidth(self.toolbox_width-18)
    self.toolbox_3_CropContour.addItem("None")
    self.toolbox_3_layout.addWidget(self.toolbox_3_CropContour)
    self.toolbox_3_layout.addSpacing(15)
    self.toolbox_3_layout.addWidget(QLabel('<b>Other parameters:</b>'))
    self.toolbox_3_dose2water = QCheckBox('convert dose-to-water')
    self.toolbox_3_dose2water.setChecked(True)
    self.toolbox_3_layout.addWidget(self.toolbox_3_dose2water)
    self.toolbox_3_DoseDenoising = QCheckBox('denoising (Deep Learning)')
    self.toolbox_3_DoseDenoising.setChecked(False)
    self.toolbox_3_layout.addWidget(self.toolbox_3_DoseDenoising)
    self.toolbox_3_layout.addSpacing(30)
    self.toolbox_3_RunButton = QPushButton('Run dose calculation')
    self.toolbox_3_layout.addWidget(self.toolbox_3_RunButton)
    self.toolbox_3_RunButton.clicked.connect(self.run_MCsquare) 
    self.toolbox_3_layout.addStretch()
    
    # initialize the 4th toolbox panel (Plan design)
    self.toolbox_4 = QWidget()
    self.toolbox_main.addItem(self.toolbox_4, 'Plan design')
    self.toolbox_4_layout = QVBoxLayout()
    self.toolbox_4.setLayout(self.toolbox_4_layout)
    self.toolbox_4_layout.addWidget(QLabel('<b>Plan name:</b>'))
    self.toolbox_4_plan_name = QLineEdit('New plan')
    self.toolbox_4_layout.addWidget(self.toolbox_4_plan_name)
    self.toolbox_4_layout.addSpacing(15)
    self.toolbox_4_layout.addWidget(QLabel('<b>Target:</b>'))
    self.toolbox_4_Target = QComboBox()
    self.toolbox_4_Target.setMaximumWidth(self.toolbox_width-18)
    self.toolbox_4_layout.addWidget(self.toolbox_4_Target)
    self.toolbox_4_layout.addSpacing(15)
    self.toolbox_4_layout.addWidget(QLabel('<b>Beams:</b>'))
    self.toolbox_4_beams =  QListWidget()
    self.toolbox_4_beams.setMaximumHeight(100)
    self.toolbox_4_beams.setContextMenuPolicy(Qt.CustomContextMenu)
    self.toolbox_4_beams.customContextMenuRequested.connect(lambda pos, list_type='beam': self.List_RightClick(pos, list_type))
    self.toolbox_4_layout.addWidget(self.toolbox_4_beams)
    ####
    #self.toolbox_4_beams = QTableWidget()
    #self.toolbox_4_beams.setColumnCount(3)
    #self.toolbox_4_beams.setHorizontalHeaderLabels(["Name", "Gantry", "Couch"])
    #self.toolbox_4_layout.addWidget(self.toolbox_4_beams)
    ####
    #self.toolbox_4_plan = QTreeWidget()
    #self.toolbox_4_plan.setColumnCount(1)
    #self.toolbox_4_plan.setHeaderHidden(True)
    #test = QTreeWidgetItem(None, ["Beam 1"])
    #test.setData(0, Qt.UserRole, 90.0) # GantryAngle
    #test.setData(0, Qt.UserRole+1, 0.0) # CouchAngle
    #test.addChild(QTreeWidgetItem(None, ["Layer 1"]))
    #QTreeWidgetItem(test, ["Layer 2"])
    #self.toolbox_4_plan.addTopLevelItem(test)
    #test = QTreeWidgetItem(None, ["Beam 2"])
    #self.toolbox_4_plan.addTopLevelItem(test)
    #test.addChild(QTreeWidgetItem(None, ["Layer 3"]))
    #QTreeWidgetItem(test, ["Layer 4"])
    #self.toolbox_4_layout.addWidget(self.toolbox_4_plan)
    ####
    self.toolbox_4_button_hLoayout = QHBoxLayout()
    self.toolbox_4_layout.addLayout(self.toolbox_4_button_hLoayout)
    self.toolbox_4_addBeam = QPushButton('Add beam')
    self.toolbox_4_addBeam.setMaximumWidth(80)
    self.toolbox_4_button_hLoayout.addWidget(self.toolbox_4_addBeam)
    self.toolbox_4_addBeam.clicked.connect(self.add_new_beam) 
    self.toolbox_4_addArc = QPushButton('Add arc')
    self.toolbox_4_addArc.setMaximumWidth(80)
    self.toolbox_4_button_hLoayout.addWidget(self.toolbox_4_addArc)
    self.toolbox_4_addArc.clicked.connect(self.add_new_arc) 
    self.toolbox_4_layout.addSpacing(30)
    self.toolbox_4_layout.addWidget(QLabel('<b>Robust optimization:</b>'))
    self.toolbox_4_RobustSettings = QLabel('')
    self.toolbox_4_layout.addWidget(self.toolbox_4_RobustSettings)
    self.toolbox_4_layout.addSpacing(10)
    self.toolbox_4_RobustnessSettingsButton = QPushButton('Modify robustness settings')
    self.toolbox_4_RobustnessSettingsButton.clicked.connect(self.set_robust_opti_settings)
    self.toolbox_4_layout.addWidget(self.toolbox_4_RobustnessSettingsButton)
    self.toolbox_4_layout.addSpacing(30)
    self.toolbox_4_CreatePlanButton = QPushButton('Create new plan')
    self.toolbox_4_layout.addWidget(self.toolbox_4_CreatePlanButton)
    self.toolbox_4_CreatePlanButton.clicked.connect(self.create_new_plan) 
    self.toolbox_4_layout.addSpacing(15)
    self.toolbox_4_ComputeBeamletButton = QPushButton('Compute beamlets')
    self.toolbox_4_layout.addWidget(self.toolbox_4_ComputeBeamletButton)
    self.toolbox_4_ComputeBeamletButton.clicked.connect(self.compute_beamlets) 
    self.toolbox_4_layout.addStretch()
    self.toolbox_4_LoadPlanButton = QPushButton('Import OpenTPS Plan')
    self.toolbox_4_layout.addWidget(self.toolbox_4_LoadPlanButton)
    self.toolbox_4_LoadPlanButton.clicked.connect(self.import_OpenTPS_Plan) 
    self.toolbox_4_layout.addSpacing(10)
    self.toolbox_4_LoadMCsquarePlanButton = QPushButton('Import MCsquare PlanPencil')
    self.toolbox_4_layout.addWidget(self.toolbox_4_LoadMCsquarePlanButton)
    self.toolbox_4_LoadMCsquarePlanButton.clicked.connect(self.import_PlanPencil) 
    self.toolbox_4_layout.addSpacing(10)
    self.update_robust_opti_settings()
    
    # initialize the 5th toolbox panel (Plan optimization)
    self.toolbox_5 = QWidget()
    self.toolbox_main.addItem(self.toolbox_5, 'Plan optimization')
    self.toolbox_5_layout = QVBoxLayout()
    self.toolbox_5.setLayout(self.toolbox_5_layout)
    self.toolbox_5_layout.addWidget(QLabel('<b>Optimization algorithm:</b>'))
    self.toolbox_5_Algorithm = QComboBox()
    self.toolbox_5_Algorithm.addItem("Beamlet-free MCsquare")
    self.toolbox_5_Algorithm.addItem("Beamlet-based BFGS")
    self.toolbox_5_Algorithm.addItem("Beamlet-based L-BFGS")
    self.toolbox_5_Algorithm.addItem("Beamlet-based FISTA")
    self.toolbox_5_Algorithm.setMaximumWidth(self.toolbox_width-18)
    self.toolbox_5_layout.addWidget(self.toolbox_5_Algorithm)
    self.toolbox_5_layout.addSpacing(15)
    self.toolbox_5_layout.addWidget(QLabel('<b>Target:</b>'))
    self.toolbox_5_Target = QComboBox()
    self.toolbox_5_Target.setMaximumWidth(self.toolbox_width-18)
    self.toolbox_5_layout.addWidget(self.toolbox_5_Target)
    self.toolbox_5_layout.addSpacing(15)
    self.toolbox_5_layout.addWidget(QLabel('<b>Prescription:</b>'))
    self.toolbox_5_Prescription = QDoubleSpinBox()
    self.toolbox_5_Prescription.setRange(0.0, 100.0)
    self.toolbox_5_Prescription.setSingleStep(1.0)
    self.toolbox_5_Prescription.setValue(60.0)
    self.toolbox_5_Prescription.setSuffix(" Gy")
    self.toolbox_5_layout.addWidget(self.toolbox_5_Prescription)
    self.toolbox_5_layout.addSpacing(15)
    self.toolbox_5_layout.addWidget(QLabel('<b>Objectives:</b>'))
    self.toolbox_5_objectives =  QListWidget()
    self.toolbox_5_objectives.setSpacing(2)
    self.toolbox_5_objectives.setAlternatingRowColors(True)
    self.toolbox_5_objectives.setMaximumHeight(150)
    self.toolbox_5_objectives.setContextMenuPolicy(Qt.CustomContextMenu)
    self.toolbox_5_objectives.customContextMenuRequested.connect(lambda pos, list_type='objective': self.List_RightClick(pos, list_type))
    self.toolbox_5_layout.addWidget(self.toolbox_5_objectives)
    self.toolbox_5_button_hLoayout = QHBoxLayout()
    self.toolbox_5_layout.addLayout(self.toolbox_5_button_hLoayout)
    self.toolbox_5_addObjective = QPushButton('Add objective')
    self.toolbox_5_addObjective.setMaximumWidth(100)
    self.toolbox_5_button_hLoayout.addWidget(self.toolbox_5_addObjective)
    self.toolbox_5_addObjective.clicked.connect(self.add_new_objective) 
    self.toolbox_5_TemplateBtn = QPushButton('Templates')
    self.toolbox_5_TemplateBtn.setMaximumWidth(100)
    self.toolbox_5_button_hLoayout.addWidget(self.toolbox_5_TemplateBtn)
    self.toolbox_5_TemplateBtn.clicked.connect(self.TemplateWindow) 
    self.toolbox_5_layout.addSpacing(30)
    self.toolbox_5_OptimizePlanButton = QPushButton('Optimize plan')
    self.toolbox_5_layout.addWidget(self.toolbox_5_OptimizePlanButton)
    self.toolbox_5_OptimizePlanButton.clicked.connect(self.optimize_plan) 
    self.toolbox_5_layout.addStretch()
    
    # initialize the 6th toolbox panel (Plan evaluation)

    self.toolbox_6 = QWidget()
    self.toolbox_main.addItem(self.toolbox_6, 'Robustness evaluation')
    self.toolbox_6_layout = QVBoxLayout()
    self.toolbox_6.setLayout(self.toolbox_6_layout)
    self.toolbox_6_layout.addWidget(QLabel('<b>Scenario selection strategy:</b>'))
    self.toolbox_6_Strategy = QLabel('')
    self.toolbox_6_layout.addWidget(self.toolbox_6_Strategy)
    self.toolbox_6_layout.addSpacing(20)
    self.toolbox_6_layout.addWidget(QLabel('<b>Scenario errors:</b>'))
    self.toolbox_6_Syst_Setup = QLabel('Systematic setup:')
    self.toolbox_6_layout.addWidget(self.toolbox_6_Syst_Setup)
    self.toolbox_6_Rand_Setup = QLabel('Random setup:')
    self.toolbox_6_layout.addWidget(self.toolbox_6_Rand_Setup)
    self.toolbox_6_Syst_Range = QLabel('Systematic range:')
    self.toolbox_6_layout.addWidget(self.toolbox_6_Syst_Range)
    self.toolbox_6_layout.addSpacing(30)
    self.toolbox_6_RobustnessSettingsButton = QPushButton('Modify robustness settings')
    self.toolbox_6_RobustnessSettingsButton.clicked.connect(self.set_robust_eval_settings)
    self.toolbox_6_layout.addWidget(self.toolbox_6_RobustnessSettingsButton)
    self.toolbox_6_layout.addSpacing(30)
    self.toolbox_6_button_hLoayout = QHBoxLayout()
    self.toolbox_6_layout.addLayout(self.toolbox_6_button_hLoayout)
    self.toolbox_6_ComputeScenariosButton = QPushButton('Compute \n Scenarios')
    self.toolbox_6_ComputeScenariosButton.setMaximumWidth(100)
    self.toolbox_6_button_hLoayout.addWidget(self.toolbox_6_ComputeScenariosButton)
    self.toolbox_6_ComputeScenariosButton.clicked.connect(self.compute_robustness_scenarios) 
    self.toolbox_6_LoadScenariosButton = QPushButton('Load saved \n scenarios')
    self.toolbox_6_LoadScenariosButton.setMaximumWidth(100)
    self.toolbox_6_button_hLoayout.addWidget(self.toolbox_6_LoadScenariosButton)
    self.toolbox_6_LoadScenariosButton.clicked.connect(self.load_robustness_scenarios) 
    self.toolbox_6_layout.addSpacing(40)
    self.toolbox_6_layout.addWidget(QLabel('<b>Displayed dose:</b>'))
    self.toolbox_6_DisplayedDose = QComboBox()
    self.toolbox_6_DisplayedDose.setMaximumWidth(self.toolbox_width-18)
    self.toolbox_6_DisplayedDose.addItems(['Nominal', 'Worst scenario', 'Voxel wise minimum', 'Voxel wise maximum'])
    self.toolbox_6_layout.addWidget(self.toolbox_6_DisplayedDose)
    self.toolbox_6_layout.addSpacing(30)
    self.toolbox_6_layout.addWidget(QLabel('<b>Target:</b>'))
    self.toolbox_6_Target = QComboBox()
    self.toolbox_6_Target.setMaximumWidth(self.toolbox_width-18)
    self.toolbox_6_layout.addWidget(self.toolbox_6_Target)
    self.toolbox_6_layout.addSpacing(10)
    self.toolbox_6_layout.addWidget(QLabel('<b>Prescription:</b>'))
    self.toolbox_6_Prescription = QDoubleSpinBox()
    self.toolbox_6_Prescription.setRange(0.0, 100.0)
    self.toolbox_6_Prescription.setSingleStep(1.0)
    self.toolbox_6_Prescription.setValue(60.0)
    self.toolbox_6_Prescription.setSuffix(" Gy")
    self.toolbox_6_layout.addWidget(self.toolbox_6_Prescription)
    self.toolbox_6_layout.addSpacing(10)
    self.toolbox_6_layout.addWidget(QLabel('<b>Evaluation metric:</b>'))
    self.toolbox_6_Metric = QComboBox()
    self.toolbox_6_Metric.setMaximumWidth(self.toolbox_width-18)
    self.toolbox_6_Metric.addItems(['D95', 'MSE'])
    self.toolbox_6_layout.addWidget(self.toolbox_6_Metric)
    self.toolbox_6_layout.addSpacing(10)
    self.toolbox_6_CI_label = QLabel('<b>Confidence interval:</b>')
    self.toolbox_6_layout.addWidget(self.toolbox_6_CI_label)
    self.toolbox_6_CI = QSlider(Qt.Horizontal)
    self.toolbox_6_CI.setMinimum(0.0)
    self.toolbox_6_CI.setMaximum(100.0)
    self.toolbox_6_CI.setValue(90.0)
    self.toolbox_6_layout.addWidget(self.toolbox_6_CI)
    self.toolbox_6_layout.addStretch()
    self.toolbox_6_CI.valueChanged.connect(self.recompute_robustness_analysis)
    self.toolbox_6_Metric.currentIndexChanged.connect(self.recompute_robustness_analysis)
    self.toolbox_6_DisplayedDose.currentIndexChanged.connect(self.recompute_robustness_analysis)
    self.toolbox_6_Target.currentIndexChanged.connect(self.recompute_robustness_analysis)
    self.toolbox_6_Prescription.valueChanged.connect(self.recompute_robustness_analysis)
    self.update_robust_eval_settings()
    self.recompute_robustness_analysis()
    
    # initialize the image viewer
    self.viewer_palette = QPalette()
    self.viewer_palette.setColor(QPalette.Window, Qt.black)
    self.viewer_layout = QGridLayout()
    self.viewer_axial = QLabel("No image loaded")
    self.viewer_axial.setAlignment(Qt.AlignCenter)
    self.viewer_axial.setAutoFillBackground(True)
    self.viewer_axial.setPalette(self.viewer_palette)
    self.viewer_coronal = QLabel("No image loaded")
    self.viewer_coronal.setAlignment(Qt.AlignCenter)
    self.viewer_coronal.setAutoFillBackground(True)
    self.viewer_coronal.setPalette(self.viewer_palette)
    self.viewer_sagittal = QLabel("No image loaded")
    self.viewer_sagittal.setAlignment(Qt.AlignCenter)
    self.viewer_sagittal.setAutoFillBackground(True)
    self.viewer_sagittal.setPalette(self.viewer_palette)
    self.viewer_DVH = qtg.PlotWidget()
    self.viewer_DVH.getPlotItem().setContentsMargins(5, 0, 20, 5)
    self.viewer_DVH.setBackground('k')
    self.viewer_DVH.setTitle("DVH")
    self.viewer_DVH.setLabel('left', 'Volume (%)')
    self.viewer_DVH.setLabel('bottom', 'Dose (Gy)')
    #self.viewer_DVH.addLegend()
    self.viewer_DVH.showGrid(x=True, y=True)
    self.viewer_DVH.setXRange(0, 100, padding=0)
    self.viewer_DVH.setYRange(0, 100, padding=0)
    self.viewer_DVH_proxy = qtg.SignalProxy(self.viewer_DVH.scene().sigMouseMoved, rateLimit=120, slot=self.DVH_mouseMoved)
    self.viewer_DVH_label = qtg.TextItem("", color=(255,255,255), fill=(0,0,0,250), anchor=(0,1))
    self.viewer_DVH_label.hide()
    self.viewer_DVH.addItem(self.viewer_DVH_label)
    self.viewer_layout.setColumnStretch(0, 1)
    self.viewer_layout.setColumnStretch(1, 1)
    self.viewer_layout.setRowStretch(0, 1)
    self.viewer_layout.setRowStretch(1, 1)
    self.viewer_layout.addWidget(self.viewer_axial, 0,0)
    self.viewer_layout.addWidget(self.viewer_sagittal, 0,1)
    self.viewer_layout.addWidget(self.viewer_coronal, 1,0)
    self.viewer_layout.addWidget(self.viewer_DVH, 1,1)
    self.main_layout.addLayout(self.viewer_layout)
    
    #QSplitter
    
  
  
  
  def TemplateWindow(self):
    # get list of contours
    ContourList = []
    for contour in self.ROI_CheckBox:
      ContourList.append(contour.text())

    # get saved templates
    Templates = ObjectiveTemplateList()
    
    # create dialog window
    dialog = ObjectiveTemplateWindow(ContourList, Templates)
    
    # get template
    if(dialog.exec()):
      for objective in Templates.list[Templates.SelectedID].Objectives:
        if objective.ROIName in ContourList:
          obj_number = self.toolbox_5_objectives.count()
          self.toolbox_5_objectives.addItem(objective.ROIName + ":\n" + objective.Metric + " " + objective.Condition + " " + str(objective.LimitValue) + " Gy   (w=" + str(objective.Weight) + ")")
          self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+0, objective.ROIName)
          self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+1, objective.Metric)
          self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+2, objective.Condition)
          self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+3, objective.LimitValue)
          self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+4, objective.Weight)



  def DVH_mouseMoved(self, evt):
    self.viewer_DVH_label.hide()

    if self.viewer_DVH.sceneBoundingRect().contains(evt[0]):
      mousePoint = self.viewer_DVH.getViewBox().mapSceneToView(evt[0])
      for item in self.viewer_DVH.scene().items():
        if hasattr(item, "DVH"):
          data = item.getData()
          y, y2 = np.interp([mousePoint.x(), mousePoint.x()*1.01], data[0], data[1])
          #if item.mouseShape().contains(mousePoint):
          # check if mouse.y is close to f(mouse.x)
          if abs(y-mousePoint.y()) < 2.0+abs(y2-y): # abs(y2-y) is to increase the distance in high gradient
            self.viewer_DVH_label.setHtml("<b><font color='#" + "{:02x}{:02x}{:02x}".format(item.DVH.ROIDisplayColor[2], item.DVH.ROIDisplayColor[1], item.DVH.ROIDisplayColor[0]) + "'>" + \
              item.name() + ":</font></b>" + \
              "<br>D95 = {:.1f} Gy".format(item.DVH.D95) + \
              "<br>D5 = {:.1f} Gy".format(item.DVH.D5) + \
              "<br>Dmean = {:.1f} Gy".format(item.DVH.Dmean) )
            self.viewer_DVH_label.setPos(mousePoint)
            if(mousePoint.x() < 50 and mousePoint.y() < 50): self.viewer_DVH_label.setAnchor((0,1))
            elif(mousePoint.x() < 50 and mousePoint.y() >= 50): self.viewer_DVH_label.setAnchor((0,0))
            elif(mousePoint.x() >= 50 and mousePoint.y() < 50): self.viewer_DVH_label.setAnchor((1,1))
            elif(mousePoint.x() >= 50 and mousePoint.y() >= 50): self.viewer_DVH_label.setAnchor((1,0))
            self.viewer_DVH_label.show()
            break

        elif hasattr(item, "DVHband"):
          #if item.isUnderMouse():
          data = item.curves[0].getData()
          y0 = np.interp(mousePoint.x(), data[0], data[1])
          data = item.curves[1].getData()
          y1 = np.interp(mousePoint.x(), data[0], data[1])
          # check if mouse is inside the band
          if(y1 < mousePoint.y() < y0):
            self.viewer_DVH_label.setHtml("<b><font color='#" + "{:02x}{:02x}{:02x}".format(item.DVHband.ROIDisplayColor[2], item.DVHband.ROIDisplayColor[1], item.DVHband.ROIDisplayColor[0]) + "'>" + \
              item.DVHband.ROIName + ":</font></b>" + \
              "<br>D95 = {:.1f} - {:.1f} Gy".format(item.DVHband.D95[0], item.DVHband.D95[1]) + \
              "<br>D5 = {:.1f} - {:.1f} Gy".format(item.DVHband.D5[0], item.DVHband.D5[1]) + \
              "<br>Dmean = {:.1f} - {:.1f} Gy".format(item.DVHband.Dmean[0], item.DVHband.Dmean[1]) )
            self.viewer_DVH_label.setPos(mousePoint)
            if(mousePoint.x() < 50 and mousePoint.y() < 50): self.viewer_DVH_label.setAnchor((0,1))
            elif(mousePoint.x() < 50 and mousePoint.y() >= 50): self.viewer_DVH_label.setAnchor((0,0))
            elif(mousePoint.x() >= 50 and mousePoint.y() < 50): self.viewer_DVH_label.setAnchor((1,1))
            elif(mousePoint.x() >= 50 and mousePoint.y() >= 50): self.viewer_DVH_label.setAnchor((1,0))
            self.viewer_DVH_label.show()
            break




  def menu_changed(self, index):
    if index == 5:
      if hasattr(self, 'toolbox_6_layout'):
        self.recompute_robustness_analysis()
    else:
      if hasattr(self, 'toolbox_1_Dose_list') and self.toolbox_main.previous_index == 5:
        self.Current_dose_changed(self.toolbox_1_Dose_list.currentRow())

    self.toolbox_main.previous_index = index



  def recompute_robustness_analysis(self):

    CI = self.toolbox_6_CI.value()
    self.toolbox_6_CI_label.setText('<b>Confidence interval:</b> &nbsp;&nbsp;&nbsp; ' + str(CI) + " %")

    # target contour
    Target_name = self.toolbox_6_Target.currentText()
    if(Target_name == ''): return
    patient_id, struct_id, contour_id = self.Patients.find_contour(Target_name)
    Target = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
    TargetPrescription = self.toolbox_6_Prescription.value()

    if(self.robustness_scenarios == []): return

    self.robustness_scenarios.DoseDistributionType = self.toolbox_6_DisplayedDose.currentText()

    if(self.robustness_scenarios.SelectionStrategy == "Dosimetric"):
      self.robustness_scenarios.dosimetric_space_analysis(self.toolbox_6_Metric.currentText(), CI, Target, TargetPrescription)
    else:
      self.robustness_scenarios.error_space_analysis(self.toolbox_6_Metric.currentText(), Target, TargetPrescription)

    # update dvh
    self.update_DVH_band_viewer()

    # update dose distribution
    self.Viewer_Dose = self.robustness_scenarios.DoseDistribution.prepare_image_for_viewer()
    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')




  def update_DVH_band_viewer(self):
    self.viewer_DVH.clear()
    for dvh_band in self.robustness_scenarios.DVH_bands:
      display = 0
      for ROI in self.ROI_CheckBox:
        if ROI.text() == dvh_band.ROIName:
          display = ROI.isChecked()
          break
      
      if display == 1:
        color = [dvh_band.ROIDisplayColor[2], dvh_band.ROIDisplayColor[1], dvh_band.ROIDisplayColor[0]]
        phigh = qtg.PlotCurveItem(dvh_band.dose, dvh_band.volume_high, pen=color, name=dvh_band.ROIName)           
        plow = qtg.PlotCurveItem(dvh_band.dose, dvh_band.volume_low, pen=color, name=dvh_band.ROIName)          
        pnominal = qtg.PlotCurveItem(dvh_band.nominalDVH.dose, dvh_band.nominalDVH.volume, pen=color, name=dvh_band.ROIName)  
        pnominal.DVH = dvh_band.nominalDVH
        pfill = qtg.FillBetweenItem(phigh, plow, brush=tuple(color + [100]))
        pfill.DVHband = dvh_band
        #self.viewer_DVH.addItem(phigh)
        #self.viewer_DVH.addItem(plow)
        self.viewer_DVH.addItem(pfill)
        self.viewer_DVH.addItem(pnominal)

    self.viewer_DVH.addItem(self.viewer_DVH_label)



  def set_robust_eval_settings(self):
    dialog = Robustness_Settings_dialog(PlanEvaluation=True, RobustParam=self.RobustEval)
    if(dialog.exec()): self.RobustEval = dialog.RobustParam
    self.update_robust_eval_settings()


  def set_robust_opti_settings(self):
    dialog = Robustness_Settings_dialog(PlanEvaluation=False, RobustParam=self.RobustOpti)
    if(dialog.exec()): self.RobustOpti = dialog.RobustParam
    self.update_robust_opti_settings()



  def update_robust_eval_settings(self):
    if(self.RobustEval["Strategy"] == 'ErrorSpace_regular'):
      self.toolbox_6_Strategy.setText('Error space (regular)')
      self.toolbox_6_Syst_Setup.setText('Syst. setup: E<sub>S</sub> = ' + str(self.RobustEval["syst_setup"]) + ' mm')
      self.toolbox_6_Rand_Setup.setText('Rand. setup: &sigma;<sub>S</sub> = ' + str(self.RobustEval["rand_setup"]) + ' mm')
      self.toolbox_6_Syst_Range.setText('Syst. range: E<sub>R</sub> = ' + str(self.RobustEval["syst_range"]) + ' %')
    elif(self.RobustEval["Strategy"] == 'ErrorSpace_stat'):
      self.toolbox_6_Strategy.setText('Error space (statistical)')
      self.toolbox_6_Syst_Setup.setText('Syst. setup: &Sigma;<sub>S</sub> = ' + str(self.RobustEval["syst_setup"]) + ' mm')
      self.toolbox_6_Rand_Setup.setText('Rand. setup: &sigma;<sub>S</sub> = ' + str(self.RobustEval["rand_setup"]) + ' mm')
      self.toolbox_6_Syst_Range.setText('Syst. range: &Sigma;<sub>R</sub> = ' + str(self.RobustEval["syst_range"]) + ' %')
    else:
      self.toolbox_6_Strategy.setText('Dosimetric space (statistical)')
      self.toolbox_6_Syst_Setup.setText('Syst. setup: &Sigma;<sub>S</sub> = ' + str(self.RobustEval["syst_setup"]) + ' mm')
      self.toolbox_6_Rand_Setup.setText('Rand. setup: &sigma;<sub>S</sub> = ' + str(self.RobustEval["rand_setup"]) + ' mm')
      self.toolbox_6_Syst_Range.setText('Syst. range: &Sigma;<sub>R</sub> = ' + str(self.RobustEval["syst_range"]) + ' %')



  def update_robust_opti_settings(self):
    if(self.RobustOpti["Strategy"] == 'Disabled'):
      self.toolbox_4_RobustSettings.setText('Disabled')
    else:
      RobustSettings = ''
      RobustSettings += 'Selection: error space<br>'
      RobustSettings += 'Syst. setup: E<sub>S</sub> = ' + str(self.RobustOpti["syst_setup"]) + ' mm<br>'
      RobustSettings += 'Rand. setup: &sigma;<sub>S</sub> = ' + str(self.RobustOpti["rand_setup"]) + ' mm<br>'
      RobustSettings += 'Syst. range: E<sub>R</sub> = ' + str(self.RobustOpti["syst_range"]) + ' %'
      self.toolbox_4_RobustSettings.setText(RobustSettings)



  def add_new_objective(self):
    # get list of contours
    ContourList = []
    for contour in self.ROI_CheckBox:
      ContourList.append(contour.text())

    # find selected plan
    plan_disp_id = self.toolbox_1_Plan_list.currentRow()
    if(plan_disp_id < 0):
      print("Error: No treatment plan selected")
      return
    plan_patient_id, plan_id = self.Patients.find_plan(plan_disp_id)
    plan = self.Patients.list[plan_patient_id].Plans[plan_id]
    
    # create dialog window
    if(plan.RobustOpti["Strategy"] == 'Disabled'): dialog = AddObjective_dialog(ContourList, RobustOpti=False)
    else: dialog = AddObjective_dialog(ContourList, RobustOpti=True)

    obj_number = self.toolbox_5_objectives.count()
    if(obj_number == 0): dialog.Contour.setCurrentText(self.toolbox_5_Target.currentText())
    else: dialog.Contour.setCurrentText(self.toolbox_5_objectives.item(obj_number-1).data(Qt.UserRole+0))
    
    # get objective inputs
    if(dialog.exec()):
      ROIName = dialog.Contour.currentText()
      Metric = dialog.Metric.currentText()
      Condition = dialog.Condition.currentText()
      LimitValue = dialog.LimitValue.value()
      Weight = dialog.Weight.value()
      Robust = dialog.Robust.isChecked()
      if(Robust == True):
        self.toolbox_5_objectives.addItem(ROIName + ":\n" + Metric + " " + Condition + " " + str(LimitValue) + " Gy   (w=" + str(Weight) + ", robust)")
      else:
        self.toolbox_5_objectives.addItem(ROIName + ":\n" + Metric + " " + Condition + " " + str(LimitValue) + " Gy   (w=" + str(Weight) + ")")
      self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+0, ROIName)
      self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+1, Metric)
      self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+2, Condition)
      self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+3, LimitValue)
      self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+4, Weight)
      self.toolbox_5_objectives.item(obj_number).setData(Qt.UserRole+5, Robust)
      
      
    
  def optimize_plan(self):
    # find selected CT image
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    if(ct_disp_id < 0):
      print("Error: No CT image selected")
      return
    ct_patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    ct = self.Patients.list[ct_patient_id].CTimages[ct_id]
    
    # find selected plan
    plan_disp_id = self.toolbox_1_Plan_list.currentRow()
    if(plan_disp_id < 0):
      print("Error: No treatment plan selected")
      return
    plan_patient_id, plan_id = self.Patients.find_plan(plan_disp_id)
    plan = self.Patients.list[plan_patient_id].Plans[plan_id]
    
    # encode optimization objectives
    Target = self.toolbox_5_Target.currentText()
    ROINames = set([Target])
    Prescription = self.toolbox_5_Prescription.value()
    plan.Objectives.setTarget(Target, Prescription)
    plan.Objectives.list = []
    for i in range(self.toolbox_5_objectives.count()):
      ROIName = self.toolbox_5_objectives.item(i).data(Qt.UserRole+0)
      Metric = self.toolbox_5_objectives.item(i).data(Qt.UserRole+1)
      Condition = self.toolbox_5_objectives.item(i).data(Qt.UserRole+2)
      LimitValue = self.toolbox_5_objectives.item(i).data(Qt.UserRole+3)
      Weight = self.toolbox_5_objectives.item(i).data(Qt.UserRole+4)
      Robust = self.toolbox_5_objectives.item(i).data(Qt.UserRole+5)
      plan.Objectives.addObjective(ROIName, Metric, Condition, LimitValue, Weight, Robust=Robust)
      ROINames.add(ROIName)
      
    # create list of contours
    contours = []
    for ROI in ROINames:
      patient_id, struct_id, contour_id = self.Patients.find_contour(ROI)
      contours.append(self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id])

    # Beamlet-free optimization algorithm
    if(self.toolbox_5_Algorithm.currentText() == "Beamlet-free MCsquare"):
      # configure MCsquare module
      mc2 = MCsquare()
      mc2.DoseName = plan.PlanName
      mc2.BDL.selected_BDL = self.toolbox_3_BDL_List.currentText()
      mc2.Scanner.selected_Scanner = self.toolbox_3_Scanner_List.currentText()
      mc2.NumProtons = self.toolbox_3_NumProtons.value()
      mc2.dose2water = self.toolbox_3_dose2water.checkState()
      mc2.PlanOptimization = "beamlet-free"

      # Crop CT image with contour:
      if(self.toolbox_3_CropContour.currentIndex() > 0):
        patient_id, struct_id, contour_id = self.Patients.find_contour(self.toolbox_3_CropContour.currentText())
        mc2.Crop_CT_contour = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
          
      # run MCsquare optimization
      mhd_dose = mc2.BeamletFree_optimization(ct, plan, contours)
      dose = RTdose().Initialize_from_MHD(mc2.DoseName, mhd_dose, ct, plan)

    # beamlet-based optimization with BFGS
    elif(self.toolbox_5_Algorithm.currentText() == "Beamlet-based BFGS"):
      if(plan.beamlets == []):
        print("Error: beamlets must be pre-computed")
        return
      w, dose_vector, ps = OptimizeWeights(plan, contours, method="BFGS")
      plan.beamlets.Weights = np.array(w, dtype=np.float32)
      plan.update_spot_weights(w)
      dose = RTdose().Initialize_from_beamlet_dose(plan.PlanName, plan.beamlets, dose_vector, ct)

    # beamlet-based optimization with L-BFGS
    elif(self.toolbox_5_Algorithm.currentText() == "Beamlet-based L-BFGS"):
      if(plan.beamlets == []):
        print("Error: beamlets must be pre-computed")
        return
      w, dose_vector, ps = OptimizeWeights(plan, contours, method="L-BFGS")
      plan.beamlets.Weights = np.array(w, dtype=np.float32)
      plan.update_spot_weights(w)
      dose = RTdose().Initialize_from_beamlet_dose(plan.PlanName, plan.beamlets, dose_vector, ct)

    # beamlet-based optimization with FISTA
    elif(self.toolbox_5_Algorithm.currentText() == "Beamlet-based FISTA"):
      if(plan.beamlets == []):
        print("Error: beamlets must be pre-computed")
        return
      w, dose_vector, ps = OptimizeWeights(plan, contours, method="FISTA")
      plan.beamlets.Weights = np.array(w, dtype=np.float32)
      plan.update_spot_weights(w)
      dose = RTdose().Initialize_from_beamlet_dose(plan.PlanName, plan.beamlets, dose_vector, ct)  

    # add dose image in the database
    self.Patients.list[plan_patient_id].RTdoses.append(dose)
    self.toolbox_1_Dose_list.addItem(dose.ImgName)
    
    # display new dose
    currentRow = self.toolbox_1_Dose_list.count()-1
    self.toolbox_1_Dose_list.setCurrentRow(currentRow)   

    # save plan
    output_path = os.path.join(self.data_path, "OpenTPS")
    if not os.path.isdir(output_path):
      os.mkdir(output_path)
    plan_file = os.path.join(output_path, "Plan_" + plan.PlanName + "_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S") + ".tps")
    plan.save(plan_file)
    
    
    
  def add_new_beam(self):
    beam_number = self.toolbox_4_beams.count()
    dialog = AddBeam_dialog("Beam " + str(beam_number+1))
    if(dialog.exec()):
      BeamName = dialog.BeamName.text()
      GantryAngle = dialog.GantryAngle.value()
      CouchAngle = dialog.CouchAngle.value()
      self.toolbox_4_beams.addItem(BeamName + ":  G=" + str(GantryAngle) + "°,  C=" + str(CouchAngle) + "°")
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+0, BeamName)
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+1, 'beam')
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+2, GantryAngle)
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+3, CouchAngle)
    
    
    
  def add_new_arc(self):
    beam_number = self.toolbox_4_beams.count()
    dialog = AddArc_dialog("Arc " + str(beam_number+1))
    if(dialog.exec()):
      ArcName = dialog.ArcName.text()
      StartGantryAngle = dialog.StartGantryAngle.value()
      StopGantryAngle = dialog.StopGantryAngle.value()
      AngularStep = dialog.AngularStep.value()
      CouchAngle = dialog.CouchAngle.value()
      self.toolbox_4_beams.addItem(ArcName + ":  G=" + str(StartGantryAngle) + " to " + str(StopGantryAngle) + "°,  C=" + str(CouchAngle) + "°")
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+0, ArcName)
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+1, 'arc')
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+2, StartGantryAngle)
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+3, CouchAngle)
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+4, StopGantryAngle)
      self.toolbox_4_beams.item(beam_number).setData(Qt.UserRole+5, AngularStep)
  
  
  
  def create_new_plan(self):
    # find selected CT image
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    if(ct_disp_id < 0):
      print("Error: No CT image selected")
      return
    patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    ct = self.Patients.list[patient_id].CTimages[ct_id]
    
    # target contour
    Target_name = self.toolbox_4_Target.currentText()
    patient_id, struct_id, contour_id = self.Patients.find_contour(Target_name)
    Target = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
    
    Scanner = self.toolbox_3_Scanner_List.currentText()
    
    # extract beam info from QListWidget
    BeamNames = []
    GantryAngles = []
    CouchAngles = []
    for i in range(self.toolbox_4_beams.count()):
      BeamType = self.toolbox_4_beams.item(i).data(Qt.UserRole+1)
      if(BeamType == "beam"):
        BeamNames.append(self.toolbox_4_beams.item(i).data(Qt.UserRole+0))
        GantryAngles.append(self.toolbox_4_beams.item(i).data(Qt.UserRole+2))
        CouchAngles.append(self.toolbox_4_beams.item(i).data(Qt.UserRole+3))
      elif(BeamType == "arc"):
        name = self.toolbox_4_beams.item(i).data(Qt.UserRole+0)
        start = self.toolbox_4_beams.item(i).data(Qt.UserRole+2)
        couch = self.toolbox_4_beams.item(i).data(Qt.UserRole+3)
        stop = self.toolbox_4_beams.item(i).data(Qt.UserRole+4)
        step = self.toolbox_4_beams.item(i).data(Qt.UserRole+5)
        if start > stop:
          start -= 360
        for b in range(math.floor((stop-start)/step)+1):
          angle = start + b * step
          if angle < 0.0: angle += 360
          print(angle)
          BeamNames.append(name + "_" + str(angle))
          GantryAngles.append(angle)
          CouchAngles.append(couch)

    # set spacing parameters
    if(self.RobustOpti["Strategy"] == 'Disabled'): 
      SpotSpacing = 7.0
      LayerSpacing = 6.0
      RTV_margin = max(SpotSpacing, LayerSpacing)
    else: 
      SpotSpacing = 7.0
      LayerSpacing = 6.0
      RTV_margin = max(SpotSpacing, LayerSpacing) + max(self.RobustOpti["syst_setup"])

    
    # Generate new plan
    plan = CreatePlanStructure(ct, Target, BeamNames, GantryAngles, CouchAngles, Scanner, RTV_margin=RTV_margin, SpotSpacing=SpotSpacing, LayerSpacing=LayerSpacing)
    plan.PlanName = self.toolbox_4_plan_name.text()
    plan.RobustOpti = self.RobustOpti
    self.Patients.list[patient_id].Plans.append(plan)
    
    # display new plan to the list
    self.toolbox_1_Plan_list.addItem(plan.PlanName)
    currentRow = self.toolbox_1_Plan_list.count()-1
    self.toolbox_1_Plan_list.setCurrentRow(currentRow)
    
  
  
  def import_PlanPencil(self):
    # find selected CT image
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    if(ct_disp_id < 0):
      print("Error: No CT image selected")
      return
    patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    ct = self.Patients.list[patient_id].CTimages[ct_id]
    
    # select file
    path, _ = QFileDialog.getOpenFileName(self, "Open MCsquare plan", self.data_path, "MCsquare plan (*.txt);;All files (*.*)")
    if(path == ""): return
    
    # import file
    plan = import_MCsquare_plan(path, ct)
    self.Patients.list[patient_id].Plans.append(plan)
    
    # display new plan
    self.toolbox_1_Plan_list.addItem(plan.PlanName)
    currentRow = self.toolbox_1_Plan_list.count()-1
    self.toolbox_1_Plan_list.setCurrentRow(currentRow)



  def import_OpenTPS_Plan(self): 
    # find selected CT image
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    if(ct_disp_id < 0):
      print("Error: No CT image selected")
      return
    patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)

    # select file
    file_path, _ = QFileDialog.getOpenFileName(self, "Load OpenTPS plan", self.data_path, "OpenTPS data (*.tps);;All files (*.*)")
    if(file_path == ""): return

    # import plan
    plan = RTplan()
    plan.load(file_path)

    # import beamlets
    Folder, File = os.path.split(file_path)
    if(plan.RobustOpti["Strategy"] == 'Disabled'): 
      beamlet_file = os.path.join(Folder, "BeamletMatrix_" + plan.SeriesInstanceUID + ".blm")
      if(os.path.isfile(beamlet_file)):
        beamlets = MCsquare_sparse_format()
        beamlets.load(beamlet_file)
        beamlets.print_memory_usage()
        plan.beamlets = beamlets
    else:
      beamlet_file = os.path.join(Folder, "BeamletMatrix_" + plan.SeriesInstanceUID + "_Nominal.blm")
      if(os.path.isfile(beamlet_file)):
        beamlets = MCsquare_sparse_format()
        beamlets.load(beamlet_file)
        beamlets.print_memory_usage()
        plan.beamlets = beamlets
      for s in range(plan.NumScenarios):
        beamlet_file = os.path.join(Folder, "BeamletMatrix_" + plan.SeriesInstanceUID + "_Scenario_" + str(s+1) + "-" + str(plan.NumScenarios) + ".blm")
        if(os.path.isfile(beamlet_file)):
          beamlets = MCsquare_sparse_format()
          beamlets.load(beamlet_file)
          beamlets.print_memory_usage()
          plan.scenarios.append(beamlets)
      
    # add plan to list
    self.Patients.list[patient_id].Plans.append(plan)
    
    # display new plan
    self.toolbox_1_Plan_list.addItem(plan.PlanName)
    currentRow = self.toolbox_1_Plan_list.count()-1
    self.toolbox_1_Plan_list.setCurrentRow(currentRow)
    
  
  
  def compute_beamlets(self):
    # find selected CT image
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    if(ct_disp_id < 0):
      print("Error: No CT image selected")
      return
    ct_patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    ct = self.Patients.list[ct_patient_id].CTimages[ct_id]
    
    # find selected plan
    plan_disp_id = self.toolbox_1_Plan_list.currentRow()
    if(plan_disp_id < 0):
      print("Error: No treatment plan selected")
      return
    plan_patient_id, plan_id = self.Patients.find_plan(plan_disp_id)
    plan = self.Patients.list[plan_patient_id].Plans[plan_id]
    
    # configure MCsquare module
    mc2 = MCsquare()
    mc2.BDL.selected_BDL = self.toolbox_3_BDL_List.currentText()
    mc2.Scanner.selected_Scanner = self.toolbox_3_Scanner_List.currentText()
    mc2.NumProtons = 5e4
    mc2.dose2water = self.toolbox_3_dose2water.checkState()
    mc2.SetupSystematicError = plan.RobustOpti["syst_setup"]
    mc2.SetupRandomError = plan.RobustOpti["rand_setup"]
    mc2.RangeSystematicError = plan.RobustOpti["syst_range"]
    if(plan.RobustOpti["Strategy"] == 'Disabled'): mc2.Robustness_Strategy = "Disabled"
    else: mc2.Robustness_Strategy = "ErrorSpace_regular"

    # Crop CT image with contour:
    if(self.toolbox_3_CropContour.currentIndex() > 0):
      patient_id, struct_id, contour_id = self.Patients.find_contour(self.toolbox_3_CropContour.currentText())
      mc2.Crop_CT_contour = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
    
    # run MCsquare simulation
    beamlets = mc2.MCsquare_beamlet_calculation(ct, plan)

    # save data
    output_path = os.path.join(self.data_path, "OpenTPS")
    if not os.path.isdir(output_path):
      os.mkdir(output_path)

    if(plan.RobustOpti["Strategy"] == 'Disabled'): 
      plan_file = os.path.join(output_path, "Plan_" + plan.PlanName + "_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S") + ".tps")
      plan.save(plan_file)
      beamlet_file = os.path.join(output_path, "BeamletMatrix_" + plan.SeriesInstanceUID + ".blm")
      beamlets.save(beamlet_file)
      plan.beamlets = beamlets
      
    else:
      plan.NumScenarios = len(beamlets[1])
      plan_file = os.path.join(output_path, "Plan_" + plan.PlanName + "_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S") + ".tps")
      plan.save(plan_file)

      plan.beamlets = beamlets[0]
      beamlet_file = os.path.join(output_path, "BeamletMatrix_" + plan.SeriesInstanceUID + "_Nominal.blm")
      plan.beamlets.save(beamlet_file)

      plan.scenarios = beamlets[1]
      for s in range(plan.NumScenarios):
        beamlet_file = os.path.join(output_path, "BeamletMatrix_" + plan.SeriesInstanceUID + "_Scenario_" + str(s+1) + "-" + str(plan.NumScenarios) + ".blm")
        plan.scenarios[s].save(beamlet_file)



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
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    if(ct_disp_id < 0):
      print("Error: No CT image selected")
      return
    ct_patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    ct = self.Patients.list[ct_patient_id].CTimages[ct_id]
    
    # find selected plan
    plan_disp_id = self.toolbox_1_Plan_list.currentRow()
    if(plan_disp_id < 0):
      print("Error: No treatment plan selected")
      return
    plan_patient_id, plan_id = self.Patients.find_plan(plan_disp_id)
    plan = self.Patients.list[plan_patient_id].Plans[plan_id]

    # find contours
    Target_name = self.toolbox_6_Target.currentText()
    patient_id, struct_id, contour_id = self.Patients.find_contour(Target_name)
    AllContours = self.Patients.list[patient_id].RTstructs[struct_id].Contours

    # configure MCsquare module
    mc2 = MCsquare()
    mc2.BDL.selected_BDL = self.toolbox_3_BDL_List.currentText()
    mc2.Scanner.selected_Scanner = self.toolbox_3_Scanner_List.currentText()
    mc2.NumProtons = self.toolbox_3_NumProtons.value()
    mc2.MaxUncertainty = self.toolbox_3_MaxUncertainty.value()
    mc2.dose2water = self.toolbox_3_dose2water.checkState()
    mc2.SetupSystematicError = self.RobustEval["syst_setup"]
    mc2.SetupRandomError = self.RobustEval["rand_setup"]
    mc2.RangeSystematicError = self.RobustEval["syst_range"]
    if(self.RobustEval["Strategy"] == 'DoseSpace'): mc2.Robustness_Strategy = "DoseSpace"
    elif(self.RobustEval["Strategy"] == 'ErrorSpace_stat'): mc2.Robustness_Strategy = "ErrorSpace_stat"
    else: mc2.Robustness_Strategy = "ErrorSpace_regular"

    # Crop CT image with contour:
    if(self.toolbox_3_CropContour.currentIndex() > 0):
      patient_id, struct_id, contour_id = self.Patients.find_contour(self.toolbox_3_CropContour.currentText())
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




  def run_MCsquare(self):
    # find selected CT image
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    if(ct_disp_id < 0):
      print("Error: No CT image selected")
      return
    ct_patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    ct = self.Patients.list[ct_patient_id].CTimages[ct_id]
    
    # find selected plan
    plan_disp_id = self.toolbox_1_Plan_list.currentRow()
    if(plan_disp_id < 0):
      print("Error: No treatment plan selected")
      return
    plan_patient_id, plan_id = self.Patients.find_plan(plan_disp_id)
    plan = self.Patients.list[plan_patient_id].Plans[plan_id]
    
    # configure MCsquare module
    mc2 = MCsquare()
    mc2.DoseName = self.toolbox_3_dose_name.text()
    mc2.BDL.selected_BDL = self.toolbox_3_BDL_List.currentText()
    mc2.Scanner.selected_Scanner = self.toolbox_3_Scanner_List.currentText()
    mc2.NumProtons = self.toolbox_3_NumProtons.value()
    mc2.MaxUncertainty = self.toolbox_3_MaxUncertainty.value()
    mc2.dose2water = self.toolbox_3_dose2water.checkState()

    # Crop CT image with contour:
    if(self.toolbox_3_CropContour.currentIndex() > 0):
      patient_id, struct_id, contour_id = self.Patients.find_contour(self.toolbox_3_CropContour.currentText())
      mc2.Crop_CT_contour = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
    
    # run MCsquare simulation
    mhd_dose = mc2.MCsquare_simulation(ct, plan)
    
    # load dose image in the database
    dose = RTdose().Initialize_from_MHD(mc2.DoseName, mhd_dose, ct, plan)
    self.Patients.list[plan_patient_id].RTdoses.append(dose)
    self.toolbox_1_Dose_list.addItem(dose.ImgName)
    
    # deep learning dose denoising
    if(self.toolbox_3_DoseDenoising.checkState()):
      DenoisedDose = RTdose().Initialize_from_MHD(mc2.DoseName + "_denoised", mhd_dose, ct, plan)
      DenoisedDose.Image = Denoise_MC_dose(dose.Image, 'dUNet_24')
      self.Patients.list[plan_patient_id].RTdoses.append(DenoisedDose)
      self.toolbox_1_Dose_list.addItem(DenoisedDose.ImgName)
    
    # display new dose
    currentRow = self.toolbox_1_Dose_list.count()-1
    self.toolbox_1_Dose_list.setCurrentRow(currentRow)
    
    
    
  def rename_item(self, list_type, row):
    if(list_type == 'CT'):
      patient_id, ct_id = self.Patients.find_CT_image(row)
      NewName, okPressed = QInputDialog.getText(self, "Rename " + list_type + " image", "New name:", QLineEdit.Normal, self.Patients.list[patient_id].CTimages[ct_id].ImgName)
      if(okPressed):
        self.Patients.list[patient_id].CTimages[ct_id].ImgName = NewName
        self.toolbox_1_CT_list.item(row).setText(NewName)
        
    elif(list_type == 'dose'):
      patient_id, dose_id = self.Patients.find_dose_image(row)
      NewName, okPressed = QInputDialog.getText(self, "Rename " + list_type + " image", "New name:", QLineEdit.Normal, self.Patients.list[patient_id].RTdoses[dose_id].ImgName)
      if(okPressed):
        self.Patients.list[patient_id].RTdoses[dose_id].ImgName = NewName
        self.toolbox_1_Dose_list.item(row).setText(NewName)
        
    elif(list_type == 'plan'):
      patient_id, plan_id = self.Patients.find_plan(row)
      NewName, okPressed = QInputDialog.getText(self, "Rename " + list_type + " plan", "New name:", QLineEdit.Normal, self.Patients.list[patient_id].Plans[plan_id].PlanName)
      if(okPressed):
        self.Patients.list[patient_id].Plans[plan_id].PlanName = NewName
        self.toolbox_1_Plan_list.item(row).setText(NewName)
        
        
    
  def delete_item(self, list_type, row):
    if(list_type == 'CT'):
      patient_id, ct_id = self.Patients.find_CT_image(row)
      DeleteReply = QMessageBox.question(self, 'Delete image', 'Delete "' + self.Patients.list[patient_id].CTimages[ct_id].ImgName + '" CT image ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
      if(DeleteReply == QMessageBox.Yes):
        del self.Patients.list[patient_id].CTimages[ct_id]
        self.toolbox_1_CT_list.takeItem(row)
        
    elif(list_type == 'dose'):
      patient_id, dose_id = self.Patients.find_dose_image(row)
      DeleteReply = QMessageBox.question(self, 'Delete image', 'Delete "' + self.Patients.list[patient_id].RTdoses[dose_id].ImgName + '" dose image ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
      if(DeleteReply == QMessageBox.Yes):
        del self.Patients.list[patient_id].RTdoses[dose_id]
        self.toolbox_1_Dose_list.takeItem(row)
        
    elif(list_type == 'plan'):
      patient_id, plan_id = self.Patients.find_plan(row)
      DeleteReply = QMessageBox.question(self, 'Delete plan', 'Delete "' + self.Patients.list[patient_id].Plans[plan_id].PlanName + '" plan ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
      if(DeleteReply == QMessageBox.Yes):
        del self.Patients.list[patient_id].Plans[plan_id]
        self.toolbox_1_Plan_list.takeItem(row)
        
    elif(list_type == 'beam'):
      self.toolbox_4_beams.takeItem(row)
        
    elif(list_type == 'objective'):
      self.toolbox_5_objectives.takeItem(row)
        
  
  
  def List_RightClick(self, pos, list_type):
    if(list_type == 'CT'):
      item = self.toolbox_1_CT_list.itemAt(pos)
      row = self.toolbox_1_CT_list.row(item)
      pos = self.toolbox_1_CT_list.mapToGlobal(pos)
   
    elif(list_type == 'dose'):
      item = self.toolbox_1_Dose_list.itemAt(pos)
      row = self.toolbox_1_Dose_list.row(item)
      pos = self.toolbox_1_Dose_list.mapToGlobal(pos)
   
    elif(list_type == 'plan'):
      item = self.toolbox_1_Plan_list.itemAt(pos)
      row = self.toolbox_1_Plan_list.row(item)
      pos = self.toolbox_1_Plan_list.mapToGlobal(pos)
      patient_id, plan_id = self.Patients.find_plan(row)
      plan = self.Patients.list[patient_id].Plans[plan_id]
   
    elif(list_type == 'beam'):
      item = self.toolbox_4_beams.itemAt(pos)
      row = self.toolbox_4_beams.row(item)
      pos = self.toolbox_4_beams.mapToGlobal(pos)
   
    elif(list_type == 'objective'):
      item = self.toolbox_5_objectives.itemAt(pos)
      row = self.toolbox_5_objectives.row(item)
      pos = self.toolbox_5_objectives.mapToGlobal(pos)
    
    else: return
    
    if(row > -1):
      self.context_menu = QMenu()
      if(list_type == 'dose'):
        self.export_action = QAction("Export")
        self.export_action.triggered.connect(lambda checked, list_type=list_type, row=row: self.export_item(list_type, row))
        self.context_menu.addAction(self.export_action)
      if(list_type != 'beam' and list_type != 'objective'):
        self.rename_action = QAction("Rename")
        self.rename_action.triggered.connect(lambda checked, list_type=list_type, row=row: self.rename_item(list_type, row))
        self.context_menu.addAction(self.rename_action)
      self.delete_action = QAction("Delete")
      self.delete_action.triggered.connect(lambda checked, list_type=list_type, row=row: self.delete_item(list_type, row))
      self.context_menu.addAction(self.delete_action)
      if(list_type == 'plan'):
        self.display_spot_action = []
        self.display_spot_action.append( QAction("Display spots (full plan)") )
        self.display_spot_action[0].triggered.connect(lambda checked, beam=-1: self.display_spots(beam))
        self.context_menu.addAction(self.display_spot_action[0])
        for b in range(len(plan.Beams)):
          self.display_spot_action.append( QAction("Display spots (Beam " + str(b+1) + ")") )
          self.display_spot_action[b+1].triggered.connect(lambda checked, beam=b: self.display_spots(beam))
          self.context_menu.addAction(self.display_spot_action[b+1])
        if(self.Viewer_Spots != []):
          self.remove_spot_action = QAction("Remove displayed spots")
          self.remove_spot_action.triggered.connect(lambda : [self.Viewer_Spots.clear(), self.Viewer_IsoCenter.clear(), self.update_viewer('axial'), self.update_viewer('coronal'), self.update_viewer('sagittal')])
          self.context_menu.addAction(self.remove_spot_action)
      self.context_menu.popup(pos)
      
  
  
  def export_item(self, list_type, row):
    output_path = os.path.join(self.data_path, "OpenTPS")
    if not os.path.isdir(output_path): os.mkdir(output_path)

    if(list_type == 'CT'):
      patient_id, ct_id = self.Patients.find_CT_image(row)
        
    elif(list_type == 'dose'):
      patient_id, dose_id = self.Patients.find_dose_image(row)
      output_file = os.path.join(output_path, "RTdose_" + self.Patients.list[patient_id].RTdoses[dose_id].ImgName + ".dcm")
      self.Patients.list[patient_id].RTdoses[dose_id].export_Dicom(output_file)
        
    elif(list_type == 'plan'):
      patient_id, plan_id = self.Patients.find_plan(row)



  def display_spots(self, beam):
    plan_disp_id = self.toolbox_1_Plan_list.currentRow()
    if(plan_disp_id < 0):
      print("Error: No treatment plan selected")
      return
    plan_patient_id, plan_id = self.Patients.find_plan(plan_disp_id)
    plan = self.Patients.list[plan_patient_id].Plans[plan_id]
    
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    if(ct_disp_id < 0):
      print("Error: No CT image selected")
      return
    ct_patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    ct = self.Patients.list[ct_patient_id].CTimages[ct_id]
    
    # compute iso-center coordinates in pixel units
    x = (plan.Beams[beam].IsocenterPosition[0] - ct.ImagePositionPatient[0]) / ct.PixelSpacing[0]
    y = (plan.Beams[beam].IsocenterPosition[1] - ct.ImagePositionPatient[1]) / ct.PixelSpacing[1]
    z = (plan.Beams[beam].IsocenterPosition[2] - ct.ImagePositionPatient[2]) / ct.PixelSpacing[2]
    self.Viewer_IsoCenter = [x,y,z]
    
    if(beam == -1):
      beams = range(len(plan.Beams))
    else:
      beams = [beam]
    
    # compute spot coordinates in pixel units
    self.Viewer_Spots = []
    spot_positions = plan.compute_cartesian_coordinates(ct, self.toolbox_3_Scanner_List.currentText(), beams)
    for position in spot_positions:
      x = (position[0] - ct.ImagePositionPatient[0]) / ct.PixelSpacing[0]
      y = (position[1] - ct.ImagePositionPatient[1]) / ct.PixelSpacing[1]
      z = (position[2] - ct.ImagePositionPatient[2]) / ct.PixelSpacing[2]
      self.Viewer_Spots.append([x,y,z])
    
    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')
      
      
  def Current_contours_changed(self):
    # find selected CT image
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    img_size = self.Patients.list[patient_id].CTimages[ct_id].GridSize
    
    #initialize image of contours for the viewer
    self.Viewer_Contours = np.zeros((img_size[0], img_size[1], img_size[2], 4))
    
    disp_id = -1
    for struct_id in range(len(self.Patients.list[0].RTstructs)):
      if(self.Patients.list[0].RTstructs[struct_id].CT_SeriesInstanceUID != self.Patients.list[patient_id].CTimages[ct_id].SeriesInstanceUID): continue
      
      for c in range(self.Patients.list[0].RTstructs[struct_id].NumContours):
        disp_id += 1
        if(self.ROI_CheckBox[disp_id].isChecked() == False): continue
        #color = list(self.Patients.list[0].RTstructs[struct_id].Contours[c].ROIDisplayColor) + [255]
        #color = np.array(color).reshape(1,1,1,4)
        #self.Viewer_Contours += self.Patients.list[0].RTstructs[struct_id].Contours[c].ContourMask.reshape(img_size[0], img_size[1], img_size[2], 1) * color
        
        self.Viewer_Contours[:,:,:,0] += self.Patients.list[0].RTstructs[struct_id].Contours[c].ContourMask * self.Patients.list[0].RTstructs[struct_id].Contours[c].ROIDisplayColor[0]
        self.Viewer_Contours[:,:,:,1] += self.Patients.list[0].RTstructs[struct_id].Contours[c].ContourMask * self.Patients.list[0].RTstructs[struct_id].Contours[c].ROIDisplayColor[1]
        self.Viewer_Contours[:,:,:,2] += self.Patients.list[0].RTstructs[struct_id].Contours[c].ContourMask * self.Patients.list[0].RTstructs[struct_id].Contours[c].ROIDisplayColor[2]
        self.Viewer_Contours[:,:,:,3] += self.Patients.list[0].RTstructs[struct_id].Contours[c].ContourMask * 255
        
        #self.Viewer_Contours += self.Patients.list[0].RTstructs[struct_id].Contours[c].ColorImage
        
    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')
    self.update_DVH_viewer()
    
   
  def Current_CT_changed(self, currentRow):
    patient_id, ct_id = self.Patients.find_CT_image(currentRow)
    self.Viewer_image =  self.Patients.list[patient_id].CTimages[ct_id].prepare_image_for_viewer()
    img_size = list(self.Viewer_image.shape)
    
    if(self.Viewer_initialized != 1):
      self.Viewer_axial_slice = round(img_size[2] / 2)
      self.Viewer_coronal_slice = round(img_size[0] / 2)
      self.Viewer_sagittal_slice = round(img_size[1] / 2)
      self.Viewer_resolution = self.Patients.list[patient_id].CTimages[ct_id].PixelSpacing
      self.Viewer_initialized = 1  
      
    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')
  
  
  
  def Current_dose_changed(self, currentRow):
    if(currentRow > -1):
      patient_id, dose_id = self.Patients.find_dose_image(currentRow)
      self.Viewer_Dose = self.Patients.list[patient_id].RTdoses[dose_id].prepare_image_for_viewer()
    else:
      self.Viewer_Dose = np.array([])
      
    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')
    self.update_DVH_viewer()
    
    
  
  # scroll event to navigate along image slices in the viewer
  def wheelEvent(self,event):
    event.accept()
    
    if(self.Viewer_initialized == 0):
      return
      
    numDegrees = event.angleDelta().y() / 8
    numSteps = numDegrees / 15
    img_size = self.Viewer_image.shape
      
    if(self.viewer_axial.underMouse()):
      self.Viewer_axial_slice += numSteps 
      if(self.Viewer_axial_slice < 0): self.Viewer_axial_slice = 0
      elif(self.Viewer_axial_slice > img_size[2]-1): self.Viewer_axial_slice = img_size[2] - 1
      self.update_viewer('axial')
    
    elif(self.viewer_coronal.underMouse()):
      self.Viewer_coronal_slice += numSteps 
      if(self.Viewer_coronal_slice < 0): self.Viewer_coronal_slice = 0
      elif(self.Viewer_coronal_slice > img_size[0]-1): self.Viewer_coronal_slice = img_size[0] - 1
      self.update_viewer('coronal')
      
    elif(self.viewer_sagittal.underMouse()):
      self.Viewer_sagittal_slice += numSteps 
      if(self.Viewer_sagittal_slice < 0): self.Viewer_sagittal_slice = 0
      elif(self.Viewer_sagittal_slice > img_size[1]-1): self.Viewer_sagittal_slice = img_size[1] - 1
      self.update_viewer('sagittal')
    
    
    
  def resizeEvent(self, event):
    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')
    
    
    
  def update_DVH_viewer(self):
    self.viewer_DVH.clear()
  
    # find selected dose image
    dose_disp_id = self.toolbox_1_Dose_list.currentRow()
    if(dose_disp_id < 0): return
    patient_id, dose_id = self.Patients.find_dose_image(dose_disp_id)
    dose = self.Patients.list[patient_id].RTdoses[dose_id]
    
    # find selected CT image
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    ct = self.Patients.list[patient_id].CTimages[ct_id]
    
    disp_id = -1
    for struct in self.Patients.list[0].RTstructs:
      if(struct.isLoaded == 0 or struct.CT_SeriesInstanceUID != ct.SeriesInstanceUID): continue
      
      for contour in struct.Contours:
        disp_id += 1
        if(disp_id >= len(self.ROI_CheckBox)): break
        if(self.ROI_CheckBox[disp_id].isChecked() == False): continue
        myDVH = DVH(dose, contour)
        pen = qtg.mkPen(color=(contour.ROIDisplayColor[2], contour.ROIDisplayColor[1], contour.ROIDisplayColor[0]), width=2)
        curve = qtg.PlotCurveItem(myDVH.dose, myDVH.volume, pen=pen, name=contour.ROIName)   
        curve.DVH = myDVH
        self.viewer_DVH.addItem(curve)

    self.viewer_DVH.addItem(self.viewer_DVH_label)
        
        
    
  def update_viewer(self, view):
    if(self.Viewer_initialized == 0):
      return
      
    # calculate scaling factor
    if(view == 'axial'): Yscaling = self.Viewer_resolution[1] / self.Viewer_resolution[0]
    elif(view == 'sagittal'): Yscaling = self.Viewer_resolution[2] / self.Viewer_resolution[1]
    else: Yscaling = self.Viewer_resolution[2] / self.Viewer_resolution[0]
            
    # paint CT image
    if(view == 'axial'): img_data = self.Viewer_image[:,:,round(self.Viewer_axial_slice)]
    elif(view == 'sagittal'): img_data = np.flip(np.transpose(self.Viewer_image[:,round(self.Viewer_sagittal_slice),:], (1,0)), 0)
    else: img_data = np.flip(np.transpose(self.Viewer_image[round(self.Viewer_coronal_slice),:,:], (1,0)), 0)
    img_data = np.require(img_data, np.uint8, 'C')
    img_size = img_data.shape
    CTimage = QImage(img_data, img_size[1], img_size[0], img_data.strides[0], QImage.Format_Indexed8)
    CTimage = CTimage.convertToFormat(QImage.Format_ARGB32)
    MergedImage = QImage(img_size[1], round(img_size[0]*Yscaling), QImage.Format_ARGB32)
    MergedImage.fill(Qt.black)
    painter = QPainter()
    painter.begin(MergedImage)
    painter.scale(1.0, Yscaling)
    painter.drawImage(0, 0, CTimage)
    
    # paint dose image
    if(self.Viewer_Dose != []):
      if(view == 'axial'): img_data = self.Viewer_Dose[:,:,round(self.Viewer_axial_slice)]
      elif(view == 'sagittal'): img_data = np.flip(np.transpose(self.Viewer_Dose[:,round(self.Viewer_sagittal_slice),:], (1,0,2)), 0)
      else: img_data = np.flip(np.transpose(self.Viewer_Dose[round(self.Viewer_coronal_slice),:,:], (1,0,2)), 0)
      img_data = np.require(img_data, np.uint8, 'C')
      DoseImage = QImage(img_data, img_size[1], img_size[0], QImage.Format_ARGB32)
      painter.setOpacity(0.3)
      painter.drawImage(0, 0, DoseImage)
      painter.setOpacity(1.0)
      
    # draw spot positions
    if(self.Viewer_Spots != []):
      pen = QPen(Qt.blue)
      pen.setWidthF(1.0)
      painter.setPen(pen)
      for spot in self.Viewer_Spots:
        if(view == 'axial'): 
          if(round(self.Viewer_axial_slice) != round(spot[2])): continue
          SpotPosition = QPointF(spot[0], spot[1])
        elif(view == 'sagittal'): 
          if(round(self.Viewer_sagittal_slice) != round(spot[0])): continue
          SpotPosition = QPointF(spot[1], img_size[0]-spot[2])
        else: 
          if(round(self.Viewer_coronal_slice) != round(spot[1])): continue
          SpotPosition = QPointF(spot[0], img_size[0]-spot[2])
        painter.drawPoint(SpotPosition)
    
    # paint contour image
    if(self.Viewer_Contours != []):
      if(view == 'axial'): img_data = self.Viewer_Contours[:,:,round(self.Viewer_axial_slice)]
      elif(view == 'sagittal'): img_data = np.flip(np.transpose(self.Viewer_Contours[:,round(self.Viewer_sagittal_slice),:], (1,0,2)), 0)
      else: img_data = np.flip(np.transpose(self.Viewer_Contours[round(self.Viewer_coronal_slice),:,:], (1,0,2)), 0)
      img_data = np.require(img_data, np.uint8, 'C')
      ContourImage = QImage(img_data, img_size[1], img_size[0], QImage.Format_ARGB32)
      painter.drawImage(0, 0, ContourImage)
      
    # draw plan iso-center
    if(self.Viewer_IsoCenter != []):
      if(view == 'axial'): IsoCenter = QPointF(self.Viewer_IsoCenter[0], self.Viewer_IsoCenter[1])
      elif(view == 'sagittal'): IsoCenter = QPointF(self.Viewer_IsoCenter[1], img_size[0]-self.Viewer_IsoCenter[2])
      else: IsoCenter = QPointF(self.Viewer_IsoCenter[0], img_size[0]-self.Viewer_IsoCenter[2])
      pen = QPen(Qt.red)
      pen.setWidthF(3.0)
      painter.setPen(pen)
      painter.drawPoint(IsoCenter)
    
    painter.end()
    
    # resize image to window scale and display
    if(view == 'axial'): 
      if(self.viewer_axial.width()/img_size[1] < self.viewer_axial.height()/(Yscaling*img_size[0])):
        self.viewer_axial.setPixmap(QPixmap.fromImage(MergedImage).scaledToWidth(self.viewer_axial.width()-10))
      else:
        self.viewer_axial.setPixmap(QPixmap.fromImage(MergedImage).scaledToHeight(self.viewer_axial.height()-10))
    elif(view == 'sagittal'): 
      if(self.viewer_sagittal.width()/img_size[1] < self.viewer_sagittal.height()/(Yscaling*img_size[0])):
        self.viewer_sagittal.setPixmap(QPixmap.fromImage(MergedImage).scaledToWidth(self.viewer_sagittal.width()-10))
      else:
        self.viewer_sagittal.setPixmap(QPixmap.fromImage(MergedImage).scaledToHeight(self.viewer_sagittal.height()-10))
    else: 
      if(self.viewer_coronal.width()/img_size[1] < self.viewer_coronal.height()/(Yscaling*img_size[0])):
        self.viewer_coronal.setPixmap(QPixmap.fromImage(MergedImage).scaledToWidth(self.viewer_coronal.width()-10))
      else:
        self.viewer_coronal.setPixmap(QPixmap.fromImage(MergedImage).scaledToHeight(self.viewer_coronal.height()-10))
    


  def load_patient_data(self):
    self.data_path = QFileDialog.getExistingDirectory(self, "Open patient data folder", self.data_path)

    self.Patients.list_dicom_files(self.data_path, 1)
    #self.Patients.print_patient_list()
    self.Patients.list[0].import_patient_data()
    
    # display CT images
    for ct in self.Patients.list[0].CTimages:
      if(ct.isLoaded == 1):
        self.toolbox_1_CT_list.addItem(ct.ImgName)
    self.toolbox_1_CT_list.setCurrentRow(self.toolbox_1_CT_list.count()-1)
    
    # display dose distributions
    for dose in self.Patients.list[0].RTdoses:
      if(dose.isLoaded == 1): 
        self.toolbox_1_Dose_list.addItem(dose.ImgName)
    self.toolbox_1_Dose_list.setCurrentRow(self.toolbox_1_Dose_list.count()-1)
      
    # display plans
    for plan in self.Patients.list[0].Plans:
      if(plan.isLoaded == 1): 
        self.toolbox_1_Plan_list.addItem(plan.PlanName)
    self.toolbox_1_Plan_list.setCurrentRow(self.toolbox_1_Plan_list.count()-1)
    
    # remove all contours from the list
    self.ROI_CheckBox = []
    while(self.toolbox_2_layout.count() != 0):
      item = self.toolbox_2_layout.takeAt(0).widget()
      if(item != None): item.setParent(None)    
      
    # display list of contours in the GUI
    ct_disp_id = self.toolbox_1_CT_list.currentRow()
    patient_id, ct_id = self.Patients.find_CT_image(ct_disp_id)
    ct = self.Patients.list[patient_id].CTimages[ct_id]
    
    for struct in self.Patients.list[0].RTstructs:
      if(struct.CT_SeriesInstanceUID != ct.SeriesInstanceUID): continue
      
      for contour in struct.Contours:
        self.ROI_CheckBox.append(QCheckBox(contour.ROIName))
        self.ROI_CheckBox[-1].setMaximumWidth(self.toolbox_width-18)
        #self.ROI_CheckBox[-1].setChecked(True)
        pixmap = QPixmap(100,100)
        pixmap.fill(QColor(contour.ROIDisplayColor[2], contour.ROIDisplayColor[1], contour.ROIDisplayColor[0], 255))
        self.ROI_CheckBox[-1].setIcon(QIcon(pixmap))
        self.ROI_CheckBox[-1].stateChanged.connect(self.Current_contours_changed) 
        self.toolbox_2_layout.addWidget(self.ROI_CheckBox[-1])
        self.toolbox_3_CropContour.addItem(contour.ROIName)
        self.toolbox_4_Target.addItem(contour.ROIName)
        self.toolbox_5_Target.addItem(contour.ROIName)
        self.toolbox_6_Target.addItem(contour.ROIName)
        
    self.toolbox_2_layout.addStretch()
    
    self.Current_contours_changed()
    

