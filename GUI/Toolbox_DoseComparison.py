
import os
from pyqtgraph import *
import numpy as np
import math 

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPalette

from Process.DVH import *

class Toolbox_DoseComparison(QWidget):

  DoseComparison_updated = pyqtSignal()
  Current_dose_changed = pyqtSignal(int)

  def __init__(self, PatientList, toolbox_width):
    QWidget.__init__(self)

    self.Patients = PatientList
    self.toolbox_width = toolbox_width
    self.DoseDiff = []
    self.DVH_list = []
    self.Contour_list = []

    self.layout = QVBoxLayout()
    self.setLayout(self.layout)
    self.layout.addWidget(QLabel('<b>Select dose 1:</b>'))
    self.Dose1_list = QListWidget()
    self.Dose1_list.setMinimumHeight(150)
    self.Dose1_list.currentRowChanged.connect(self.Selected_dose_changed)
    self.layout.addWidget(self.Dose1_list)
    self.layout.addSpacing(10)
    self.layout.addWidget(QLabel('<b>Select dose 2:</b>'))
    self.Dose2_list = QListWidget()
    self.Dose2_list.setMinimumHeight(150)
    self.Dose2_list.currentRowChanged.connect(self.Selected_dose_changed)
    self.layout.addWidget(self.Dose2_list)
    self.layout.addSpacing(10)
    self.MSE_label = QLabel('<b>MSE:</b> 0.0 Gy')
    self.layout.addWidget(self.MSE_label)
    self.RMSE_label = QLabel('<b>RMSE:</b> 0.0 Gy')
    self.layout.addWidget(self.RMSE_label)
    self.layout.addSpacing(10)
    self.layout.addWidget(QLabel('<b>Histogram:</b>'))
    self.histogram = PlotWidget()
    self.histogram.getPlotItem().setContentsMargins(5, 0, 20, 5)
    self.histogram.setBackground(None)
    self.histogram.getAxis('bottom').setTextPen('k')
    self.histogram.hideAxis('left')
    self.histogram.setLabel('bottom', 'dose1 - dose2 (Gy)')
    self.layout.addWidget(self.histogram)




  def Selected_dose_changed(self):
    row1 = self.Dose1_list.currentRow()
    self.Current_dose_changed.emit(row1)
    self.Compute_dose_difference()



  def Compute_dose_difference(self):
    row1 = self.Dose1_list.currentRow()
    row2 = self.Dose2_list.currentRow()

    if(row1 < 0): return
    
    # find dose distributions
    patient_id, dose_id = self.Patients.find_dose_image(row1)
    dose1 = self.Patients.list[patient_id].RTdoses[dose_id]
    if(row2 < 0):
      dose2 = dose1.copy()
      dose2.Image = np.zeros(dose1.Image.shape)
    else:
      patient_id, dose_id = self.Patients.find_dose_image(row2)
      dose2 = self.Patients.list[patient_id].RTdoses[dose_id]

    # compute dose difference
    DoseDiff = dose1.copy()
    DoseDiff.Image -= dose2.Image
    self.DoseDiff = DoseDiff.prepare_image_for_viewer(allow_negative=True)

    # compute histogram
    if(row2 < 0): mask = dose1.Image!=0
    else: mask = np.logical_or(dose1.Image!=0, dose2.Image!=0)
    y,x = np.histogram(DoseDiff.Image[mask], bins=25)
    bin_starts = x[0:-1]
    bin_width = x[1:] - x[0:-1]
    self.histogram.clear()
    bars = BarGraphItem(x0=bin_starts, height=y, width=bin_width)   
    self.histogram.addItem(bars)

    # compute MSE
    MSE = (DoseDiff.Image**2).mean()
    self.MSE_label.setText("<b>MSE:</b> %.2f Gy" % MSE)
    self.RMSE_label.setText("<b>RMSE:</b> %.2f Gy" % math.sqrt(MSE))

    # prepare DVH
    self.DVH_list = []
    for contour in self.Contour_list:
      dvh = DVH(dose1, contour)
      dvh.ROIName += " (dose1)"
      self.DVH_list.append(dvh)
      if(row2 >= 0):
        dvh = DVH(dose2, contour)
        dvh.LineStyle = "dashed"
        dvh.ROIName += " (dose2)"
        self.DVH_list.append(dvh)

    self.DoseComparison_updated.emit()



  def Add_dose(self, Name):
    # add dose to the list
    self.Dose1_list.addItem(Name)
    self.Dose2_list.addItem(Name)

    # display new dose
    currentRow = self.Dose1_list.count()-1
    self.Dose1_list.setCurrentRow(currentRow)



  def Update_contours(self, contours):
    self.Contour_list = contours
    self.Compute_dose_difference()