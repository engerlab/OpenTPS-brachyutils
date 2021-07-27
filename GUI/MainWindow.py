from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPainter, QPalette, QPen
from PyQt5.QtCore import Qt, QDir, QPointF
import pyqtgraph as qtg
import numpy as np
import datetime
import os

from GUI.Toolbox_PatientData import *
from GUI.Toolbox_ROI import *
from GUI.Toolbox_DoseComputation import *
from GUI.Toolbox_PlanDesign import *
from GUI.Toolbox_PlanOptimization import *
from GUI.Toolbox_PlanEvaluation import *
from GUI.Toolbox_ImageRegistration import *
from GUI.Toolbox_DoseComparison import *
from GUI.Viewer_Grid import *

from Process.PatientData import *
from Process.DVH import *
from Process.MCsquare_BDL import *

class MainWindow(QMainWindow):

  Selected_contours_changed = pyqtSignal(list)

  def __init__(self):
    # initialize data
    self.Patients = PatientList()
    self.data_path = QDir.currentPath()
    self.Dose_calculation_param = {"BDL": "", "Scanner": "", "NumProtons": 1e7, "MaxUncertainty": 2.0, "CropContour": "None", "dose2water": True}
    self.CT_disp_ID = -1
    self.Dose_disp_ID = -1
    self.Plan_disp_ID = -1
  
    # initialize the main window
    QMainWindow.__init__(self)
    self.setWindowTitle('OpenTPS')
    self.resize(1400, 920)
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
    self.toolbox_1 = Toolbox_PatientData(self.Patients, self.toolbox_width)
    self.toolbox_main.addItem(self.toolbox_1, 'Patient data')
    self.toolbox_1.Current_CT_changed.connect(self.Current_CT_changed)
    self.toolbox_1.Current_dose_changed.connect(self.Current_dose_changed)
    self.toolbox_1.Current_plan_changed.connect(self.Current_plan_changed)
    self.toolbox_1.Data_path_changed.connect(self.Data_path_changed)
    self.toolbox_1.Viewer_display_spots.connect(self.display_spots)
    self.toolbox_1.Viewer_clear_spots.connect(self.clear_spots_viewer)

    # initialize the 2nd toolbox panel (ROI)
    self.toolbox_2 = Toolbox_ROI(self.Patients, self.toolbox_width)
    self.toolbox_main.addItem(self.toolbox_2, 'ROI')
    self.toolbox_1.ROI_list_changed.connect(self.toolbox_2.reload_ROI_list)
    self.toolbox_2.Current_contours_changed.connect(self.Current_contours_changed)
    
    # initialize the 3rd toolbox panel (Dose computation)
    self.toolbox_3 = Toolbox_DoseComputation(self.Patients, self.toolbox_width)
    self.toolbox_main.addItem(self.toolbox_3, 'Dose computation')
    self.toolbox_3.New_dose_created.connect(self.toolbox_1.Add_dose)
    self.toolbox_2.New_contour_added.connect(self.toolbox_3.Add_new_contour)
    self.toolbox_2.Contour_removed.connect(self.toolbox_3.Remove_contour)
    self.Update_dose_calculation_param(self.toolbox_3.Dose_calculation_param)
    self.toolbox_3.Dose_calculation_param_changed.connect(self.Update_dose_calculation_param)
    
    # initialize the 4th toolbox panel (Plan design)
    self.toolbox_4 = Toolbox_PlanDesign(self.Patients, self.toolbox_width)
    self.toolbox_main.addItem(self.toolbox_4, 'Plan design')
    self.toolbox_4.Update_dose_calculation_param(self.toolbox_3.Dose_calculation_param)
    self.toolbox_3.Dose_calculation_param_changed.connect(self.toolbox_4.Update_dose_calculation_param)
    self.toolbox_2.New_contour_added.connect(self.toolbox_4.Add_new_contour)
    self.toolbox_2.Contour_removed.connect(self.toolbox_4.Remove_contour)
    self.toolbox_4.New_plan_created.connect(self.toolbox_1.Add_plan)
    self.toolbox_1.Data_path_changed.connect(self.toolbox_4.Data_path_changed)
    
    # initialize the 5th toolbox panel (Plan optimization)
    self.toolbox_5 = Toolbox_PlanOptimization(self.Patients, self.toolbox_width)
    self.toolbox_main.addItem(self.toolbox_5, 'Plan optimization')
    self.toolbox_2.New_contour_added.connect(self.toolbox_5.Add_new_contour)
    self.toolbox_2.Contour_removed.connect(self.toolbox_5.Remove_contour)
    self.toolbox_5.Update_dose_calculation_param(self.toolbox_3.Dose_calculation_param)
    self.toolbox_3.Dose_calculation_param_changed.connect(self.toolbox_5.Update_dose_calculation_param)
    self.toolbox_5.New_dose_created.connect(self.toolbox_1.Add_dose)
    self.toolbox_1.Data_path_changed.connect(self.toolbox_5.Data_path_changed)
    
    # initialize the 6th toolbox panel (Plan evaluation)
    self.toolbox_6 = Toolbox_PlanEvaluation(self.Patients, self.toolbox_width)
    self.toolbox_main.addItem(self.toolbox_6, 'Robustness evaluation')
    self.toolbox_2.New_contour_added.connect(self.toolbox_6.Add_new_contour)
    self.toolbox_2.Contour_removed.connect(self.toolbox_6.Remove_contour)
    self.toolbox_5.Update_dose_calculation_param(self.toolbox_6.Dose_calculation_param)
    self.toolbox_3.Dose_calculation_param_changed.connect(self.toolbox_6.Update_dose_calculation_param)
    self.toolbox_1.Data_path_changed.connect(self.toolbox_6.Data_path_changed)
    self.toolbox_6.Robustness_analysis_recomputed.connect(self.update_robustness_viewer)

    # initialize the 7th toolbox panel (Image registration)
    self.toolbox_7 = Toolbox_ImageRegistration(self.Patients, self.toolbox_width)
    self.toolbox_main.addItem(self.toolbox_7, 'Image registration')
    self.toolbox_7.Registration_updated.connect(self.update_registration_viewer)
    self.toolbox_7.New_CT_created.connect(self.toolbox_1.Add_CT)
    self.toolbox_1.New_CT_created.connect(self.toolbox_7.Add_CT)
    self.toolbox_1.CT_removed.connect(self.toolbox_7.Remove_CT)
    self.toolbox_1.CT_renamed.connect(self.toolbox_7.Rename_CT)
    self.toolbox_2.New_contour_added.connect(self.toolbox_7.Add_new_contour)
    self.toolbox_2.Contour_removed.connect(self.toolbox_7.Remove_contour)

    # initialize the 8th toolbox panel (Dose comparison)
    self.toolbox_8 = Toolbox_DoseComparison(self.Patients, self.toolbox_width)
    self.toolbox_main.addItem(self.toolbox_8, 'Dose comparison')
    self.toolbox_8.DoseComparison_updated.connect(self.update_DoseComparison_viewer)
    self.toolbox_8.Current_dose_changed.connect(self.Current_dose_changed)
    self.toolbox_8.Current_dose_changed.connect(self.toolbox_1.Dose_list.setCurrentRow)
    self.toolbox_1.Current_dose_changed.connect(self.toolbox_8.Dose1_list.setCurrentRow)
    self.toolbox_1.New_dose_created.connect(self.toolbox_8.Add_dose)
    self.toolbox_3.New_dose_created.connect(self.toolbox_8.Add_dose)
    self.toolbox_5.New_dose_created.connect(self.toolbox_8.Add_dose)
    self.Selected_contours_changed.connect(self.toolbox_8.Update_contours)
    
    # initialize the image viewer
    self.ViewerGrid = Viewer_Grid()
    self.main_layout.addLayout(self.ViewerGrid)
    
    self.GUI_initialized = 1



  def Update_dose_calculation_param(self, param):
    self.Dose_calculation_param = param
    
  

  def Data_path_changed(self, data_path):
    self.data_path = data_path



  def menu_changed(self, index):
    if(not hasattr(self, 'GUI_initialized')): return

    # Robustness evaluation views
    if index == 5:
      if(self.toolbox_6.robustness_scenarios == []):
        self.Current_CT_changed(self.CT_disp_ID)
        self.Current_dose_changed(self.Dose_disp_ID)

      else:
        self.update_robustness_viewer()

    # Image registration views
    elif index == 6:
      self.update_registration_viewer()

    # Dose comparison views
    elif index == 7:
      self.update_DoseComparison_viewer()

    # Normal views
    else:
      if self.toolbox_main.previous_index > 4:
        self.Current_CT_changed(self.CT_disp_ID)
        self.Current_dose_changed(self.Dose_disp_ID)

    self.toolbox_main.previous_index = index



  def update_DoseComparison_viewer(self):
    if(self.toolbox_main.currentIndex() != 7): return
    if(self.toolbox_8.DoseDiff != []): self.ViewerGrid.set_Dose_images(self.toolbox_8.DoseDiff)
    if(self.toolbox_8.DVH_list != []): self.ViewerGrid.set_DVH(self.toolbox_8.DVH_list)



  def update_registration_viewer(self):
    if(self.toolbox_7.diff_image_viewer == []): return

    self.ViewerGrid.clear_all()
    self.ViewerGrid.set_CT_images(self.toolbox_7.diff_image_viewer, self.toolbox_7.PixelSpacing_viewer)
    if(self.toolbox_7.ROI_box_viewer != []): self.ViewerGrid.set_Contour_images(self.toolbox_7.ROI_box_viewer)



  def update_robustness_viewer(self):
    if(self.toolbox_6.robustness_scenarios == []): return

    # update dvh
    self.update_DVH_band_viewer()

    # update dose distribution
    Viewer_Dose = self.toolbox_6.robustness_scenarios.DoseDistribution.prepare_image_for_viewer()
    self.ViewerGrid.set_Dose_images(Viewer_Dose)



  def update_DVH_band_viewer(self):
    DVHband_list = []
    for dvh_band in self.toolbox_6.robustness_scenarios.DVH_bands:
      display = 0
      for ROI in self.toolbox_2.ROI_CheckBox:
        if ROI.text() == dvh_band.ROIName:
          display = ROI.isChecked()
          break
      
      if display == 1: DVHband_list.append(dvh_band)

    self.ViewerGrid.set_DVHband(DVHband_list)



  def display_spots(self, beam):
    if(self.Plan_disp_ID < 0):
      print("Error: No treatment plan selected")
      return
    plan_patient_id, plan_id = self.Patients.find_plan(self.Plan_disp_ID)
    plan = self.Patients.list[plan_patient_id].Plans[plan_id]
    
    if(self.CT_disp_ID < 0):
      print("Error: No CT image selected")
      return
    ct_patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)
    ct = self.Patients.list[ct_patient_id].CTimages[ct_id]
    
    # compute iso-center coordinates in pixel units
    x = (plan.Beams[beam].IsocenterPosition[0] - ct.ImagePositionPatient[0]) / ct.PixelSpacing[0]
    y = (plan.Beams[beam].IsocenterPosition[1] - ct.ImagePositionPatient[1]) / ct.PixelSpacing[1]
    z = (plan.Beams[beam].IsocenterPosition[2] - ct.ImagePositionPatient[2]) / ct.PixelSpacing[2]

    self.ViewerGrid.Display_IsoCenter([x,y,z])
    
    if(beam == -1):
      beams = range(len(plan.Beams))
    else:
      beams = [beam]

    # load BDL
    BDL = MCsquare_BDL()
    BDL.import_BDL(self.Dose_calculation_param["BDL"])
    
    # compute spot coordinates in pixel units
    Viewer_Spots = []
    spot_positions = plan.compute_cartesian_coordinates(ct, self.Dose_calculation_param["Scanner"], beams, RangeShifters=BDL.RangeShifters)
    for position in spot_positions:
      x = (position[0] - ct.ImagePositionPatient[0]) / ct.PixelSpacing[0]
      y = (position[1] - ct.ImagePositionPatient[1]) / ct.PixelSpacing[1]
      z = (position[2] - ct.ImagePositionPatient[2]) / ct.PixelSpacing[2]
      Viewer_Spots.append([x,y,z])
    
    self.ViewerGrid.Display_Spots(Viewer_Spots)


  
  def Current_plan_changed(self, Plan_disp_ID):
    self.Plan_disp_ID = Plan_disp_ID
    self.toolbox_3.Plan_disp_ID = Plan_disp_ID
    self.toolbox_4.Plan_disp_ID = Plan_disp_ID
    self.toolbox_5.Plan_disp_ID = Plan_disp_ID
    self.toolbox_6.Plan_disp_ID = Plan_disp_ID

      
      
  def Current_contours_changed(self):
    # find selected CT image
    patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)
    img_size = self.Patients.list[patient_id].CTimages[ct_id].GridSize
    
    #initialize image of contours for the viewer
    selected_contours = []
    Viewer_Contours = np.zeros((img_size[0], img_size[1], img_size[2], 4), dtype=np.int8)
    
    disp_id = -1
    for struct_id in range(len(self.Patients.list[0].RTstructs)):
      if(self.Patients.list[0].RTstructs[struct_id].CT_SeriesInstanceUID != self.Patients.list[patient_id].CTimages[ct_id].SeriesInstanceUID): continue
      
      for c in range(self.Patients.list[0].RTstructs[struct_id].NumContours):
        disp_id += 1
        if(disp_id >= len(self.toolbox_2.ROI_CheckBox)): break
        if(self.toolbox_2.ROI_CheckBox[disp_id].isChecked() == False): continue

        selected_contours.append(self.Patients.list[0].RTstructs[struct_id].Contours[c])
        Viewer_Contours[:,:,:,0] += self.Patients.list[0].RTstructs[struct_id].Contours[c].ContourMask * self.Patients.list[0].RTstructs[struct_id].Contours[c].ROIDisplayColor[0]
        Viewer_Contours[:,:,:,1] += self.Patients.list[0].RTstructs[struct_id].Contours[c].ContourMask * self.Patients.list[0].RTstructs[struct_id].Contours[c].ROIDisplayColor[1]
        Viewer_Contours[:,:,:,2] += self.Patients.list[0].RTstructs[struct_id].Contours[c].ContourMask * self.Patients.list[0].RTstructs[struct_id].Contours[c].ROIDisplayColor[2]
        Viewer_Contours[:,:,:,3] += self.Patients.list[0].RTstructs[struct_id].Contours[c].ContourMask * 255
        
    self.Selected_contours_changed.emit(selected_contours)
    self.ViewerGrid.set_Contour_images(Viewer_Contours)
    self.update_DVH_viewer()

    
   
  def Current_CT_changed(self, CT_disp_ID):

    self.CT_disp_ID = CT_disp_ID
    self.toolbox_2.CT_disp_ID = CT_disp_ID
    self.toolbox_3.CT_disp_ID = CT_disp_ID
    self.toolbox_4.CT_disp_ID = CT_disp_ID
    self.toolbox_5.CT_disp_ID = CT_disp_ID
    self.toolbox_6.CT_disp_ID = CT_disp_ID

    if CT_disp_ID < 0: 
      self.ViewerGrid.clear_CT_images()
      return

    patient_id, ct_id = self.Patients.find_CT_image(CT_disp_ID)
    Viewer_CT =  self.Patients.list[patient_id].CTimages[ct_id].prepare_image_for_viewer()
    resolution = self.Patients.list[patient_id].CTimages[ct_id].PixelSpacing
    self.ViewerGrid.set_CT_images(Viewer_CT, resolution)

    self.Current_contours_changed()
  
  
  
  def Current_dose_changed(self, Dose_disp_ID):
    self.Dose_disp_ID = Dose_disp_ID

    if Dose_disp_ID < 0: 
      self.ViewerGrid.clear_Dose_images()

    else:
      patient_id, dose_id = self.Patients.find_dose_image(Dose_disp_ID)
      Viewer_Dose = self.Patients.list[patient_id].RTdoses[dose_id].prepare_image_for_viewer()
      self.ViewerGrid.set_Dose_images(Viewer_Dose)
      
    self.update_DVH_viewer()
    
    
  
  # scroll event to navigate along image slices in the viewer
  def wheelEvent(self,event):
    event.accept()
      
    numDegrees = event.angleDelta().y() / 8
    numSteps = numDegrees / 15

    self.ViewerGrid.scroll_viewers(numSteps)
    
    
    
  def resizeEvent(self, event):
    self.ViewerGrid.update_all_views()
    
    
    
  def update_DVH_viewer(self):  
    # find selected dose image
    if(self.Dose_disp_ID < 0): return
    patient_id, dose_id = self.Patients.find_dose_image(self.Dose_disp_ID)
    dose = self.Patients.list[patient_id].RTdoses[dose_id]
    
    # find selected CT image
    patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)
    ct = self.Patients.list[patient_id].CTimages[ct_id]
    
    disp_id = -1
    DVH_list = []
    for struct in self.Patients.list[0].RTstructs:
      if(struct.isLoaded == 0 or struct.CT_SeriesInstanceUID != ct.SeriesInstanceUID): continue
      
      for contour in struct.Contours:
        disp_id += 1
        if(disp_id >= len(self.toolbox_2.ROI_CheckBox)): break
        if(self.toolbox_2.ROI_CheckBox[disp_id].isChecked() == False): continue
        DVH_list.append(DVH(dose, contour))

    self.ViewerGrid.set_DVH(DVH_list)



  def clear_spots_viewer(self):
    self.ViewerGrid.Clear_Spots()
    self.ViewerGrid.Clear_IsoCenter()
  
    

