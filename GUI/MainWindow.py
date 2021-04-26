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

from Process.PatientData import *
from Process.DVH import *
from Process.MCsquare_BDL import *

class MainWindow(QMainWindow):
  def __init__(self):
    # initialize data
    self.Patients = PatientList()
    self.data_path = QDir.currentPath()
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
    
    self.GUI_initialized = 1



  def Update_dose_calculation_param(self, param):
    self.Dose_calculation_param = param
    
  

  def Data_path_changed(self, data_path):
    self.data_path = data_path



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

    # Normal views
    else:
      if self.toolbox_main.previous_index > 4:
        self.Current_CT_changed(self.CT_disp_ID)
        self.Current_dose_changed(self.Dose_disp_ID)

    self.toolbox_main.previous_index = index



  def update_robustness_viewer(self):
    if(self.toolbox_6.robustness_scenarios == []): return

    # update dvh
    self.update_DVH_band_viewer()

    # update dose distribution
    self.Viewer_Dose = self.toolbox_6.robustness_scenarios.DoseDistribution.prepare_image_for_viewer()
    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')



  def update_registration_viewer(self):
    if(self.toolbox_7.diff_image_viewer == []): return

    self.Viewer_CT = self.toolbox_7.diff_image_viewer
    self.Viewer_Dose = np.array([])

    img_size = list(self.Viewer_CT.shape)
    self.Viewer_axial_slice = round(img_size[2] / 2)
    self.Viewer_coronal_slice = round(img_size[0] / 2)
    self.Viewer_sagittal_slice = round(img_size[1] / 2)
    self.Viewer_resolution = self.toolbox_7.PixelSpacing_viewer
    self.Viewer_initialized = 1  

    if(self.toolbox_7.ROI_box_viewer == []):
      self.Viewer_Contours = np.array([])
    else:
      self.Viewer_Contours = self.toolbox_7.ROI_box_viewer

    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')



  def update_DVH_band_viewer(self):
    self.viewer_DVH.clear()
    for dvh_band in self.toolbox_6.robustness_scenarios.DVH_bands:
      display = 0
      for ROI in self.toolbox_2.ROI_CheckBox:
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
    self.Viewer_IsoCenter = [x,y,z]
    
    if(beam == -1):
      beams = range(len(plan.Beams))
    else:
      beams = [beam]

    # load BDL
    BDL = MCsquare_BDL()
    BDL.import_BDL(self.Dose_calculation_param["BDL"])
    
    # compute spot coordinates in pixel units
    self.Viewer_Spots = []
    spot_positions = plan.compute_cartesian_coordinates(ct, self.Dose_calculation_param["Scanner"], beams, RangeShifters=BDL.RangeShifters)
    for position in spot_positions:
      x = (position[0] - ct.ImagePositionPatient[0]) / ct.PixelSpacing[0]
      y = (position[1] - ct.ImagePositionPatient[1]) / ct.PixelSpacing[1]
      z = (position[2] - ct.ImagePositionPatient[2]) / ct.PixelSpacing[2]
      self.Viewer_Spots.append([x,y,z])
    
    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')


  
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
    self.Viewer_Contours = np.zeros((img_size[0], img_size[1], img_size[2], 4))
    
    disp_id = -1
    for struct_id in range(len(self.Patients.list[0].RTstructs)):
      if(self.Patients.list[0].RTstructs[struct_id].CT_SeriesInstanceUID != self.Patients.list[patient_id].CTimages[ct_id].SeriesInstanceUID): continue
      
      for c in range(self.Patients.list[0].RTstructs[struct_id].NumContours):
        disp_id += 1
        if(disp_id >= len(self.toolbox_2.ROI_CheckBox)): break
        if(self.toolbox_2.ROI_CheckBox[disp_id].isChecked() == False): continue
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
    
   
  def Current_CT_changed(self, CT_disp_ID):

    self.CT_disp_ID = CT_disp_ID
    self.toolbox_2.CT_disp_ID = CT_disp_ID
    self.toolbox_3.CT_disp_ID = CT_disp_ID
    self.toolbox_4.CT_disp_ID = CT_disp_ID
    self.toolbox_5.CT_disp_ID = CT_disp_ID
    self.toolbox_6.CT_disp_ID = CT_disp_ID

    if CT_disp_ID < 0: 
      self.Viewer_initialized = 0
      self.Viewer_CT = np.array([])
      self.update_viewer('axial')
      self.update_viewer('coronal')
      self.update_viewer('sagittal')
      self.update_DVH_viewer()
      return

    patient_id, ct_id = self.Patients.find_CT_image(CT_disp_ID)
    self.Viewer_CT =  self.Patients.list[patient_id].CTimages[ct_id].prepare_image_for_viewer()
    img_size = list(self.Viewer_CT.shape)
    
    self.Viewer_axial_slice = round(img_size[2] / 2)
    self.Viewer_coronal_slice = round(img_size[0] / 2)
    self.Viewer_sagittal_slice = round(img_size[1] / 2)
    self.Viewer_resolution = self.Patients.list[patient_id].CTimages[ct_id].PixelSpacing
    self.Viewer_initialized = 1  

    self.Current_contours_changed()
  
  
  
  def Current_dose_changed(self, Dose_disp_ID):
    if Dose_disp_ID < 0: 
      self.Viewer_Dose = np.array([])

    else:
      self.Dose_disp_ID = Dose_disp_ID
      patient_id, dose_id = self.Patients.find_dose_image(Dose_disp_ID)
      self.Viewer_Dose = self.Patients.list[patient_id].RTdoses[dose_id].prepare_image_for_viewer()
      
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
    img_size = self.Viewer_CT.shape
      
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
    if(self.Dose_disp_ID < 0): return
    patient_id, dose_id = self.Patients.find_dose_image(self.Dose_disp_ID)
    dose = self.Patients.list[patient_id].RTdoses[dose_id]
    
    # find selected CT image
    patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)
    ct = self.Patients.list[patient_id].CTimages[ct_id]
    
    disp_id = -1
    for struct in self.Patients.list[0].RTstructs:
      if(struct.isLoaded == 0 or struct.CT_SeriesInstanceUID != ct.SeriesInstanceUID): continue
      
      for contour in struct.Contours:
        disp_id += 1
        if(disp_id >= len(self.toolbox_2.ROI_CheckBox)): break
        if(self.toolbox_2.ROI_CheckBox[disp_id].isChecked() == False): continue
        myDVH = DVH(dose, contour)
        pen = qtg.mkPen(color=(contour.ROIDisplayColor[2], contour.ROIDisplayColor[1], contour.ROIDisplayColor[0]), width=2)
        curve = qtg.PlotCurveItem(myDVH.dose, myDVH.volume, pen=pen, name=contour.ROIName)   
        curve.DVH = myDVH
        self.viewer_DVH.addItem(curve)

    self.viewer_DVH.addItem(self.viewer_DVH_label)



  def clear_spots_viewer(self):
    self.Viewer_Spots.clear()
    self.Viewer_IsoCenter.clear()
    self.update_viewer('axial')
    self.update_viewer('coronal')
    self.update_viewer('sagittal')
        
        
    
  def update_viewer(self, view):
    if(self.Viewer_initialized == 0):
      return
      
    # calculate scaling factor
    if(view == 'axial'): Yscaling = self.Viewer_resolution[1] / self.Viewer_resolution[0]
    elif(view == 'sagittal'): Yscaling = self.Viewer_resolution[2] / self.Viewer_resolution[1]
    else: Yscaling = self.Viewer_resolution[2] / self.Viewer_resolution[0]
            
    # paint CT image
    if(view == 'axial'): img_data = self.Viewer_CT[:,:,round(self.Viewer_axial_slice)]
    elif(view == 'sagittal'): img_data = np.flip(np.transpose(self.Viewer_CT[:,round(self.Viewer_sagittal_slice),:], (1,0)), 0)
    else: img_data = np.flip(np.transpose(self.Viewer_CT[round(self.Viewer_coronal_slice),:,:], (1,0)), 0)
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
        self.viewer_axial.setPixmap(QPixmap.fromImage(MergedImage).scaledToWidth(self.viewer_axial.width()-10, mode=Qt.SmoothTransformation))
      else:
        self.viewer_axial.setPixmap(QPixmap.fromImage(MergedImage).scaledToHeight(self.viewer_axial.height()-10, mode=Qt.SmoothTransformation))
    elif(view == 'sagittal'): 
      if(self.viewer_sagittal.width()/img_size[1] < self.viewer_sagittal.height()/(Yscaling*img_size[0])):
        self.viewer_sagittal.setPixmap(QPixmap.fromImage(MergedImage).scaledToWidth(self.viewer_sagittal.width()-10, mode=Qt.SmoothTransformation))
      else:
        self.viewer_sagittal.setPixmap(QPixmap.fromImage(MergedImage).scaledToHeight(self.viewer_sagittal.height()-10, mode=Qt.SmoothTransformation))
    else: 
      if(self.viewer_coronal.width()/img_size[1] < self.viewer_coronal.height()/(Yscaling*img_size[0])):
        self.viewer_coronal.setPixmap(QPixmap.fromImage(MergedImage).scaledToWidth(self.viewer_coronal.width()-10, mode=Qt.SmoothTransformation))
      else:
        self.viewer_coronal.setPixmap(QPixmap.fromImage(MergedImage).scaledToHeight(self.viewer_coronal.height()-10, mode=Qt.SmoothTransformation))
    


  
    

