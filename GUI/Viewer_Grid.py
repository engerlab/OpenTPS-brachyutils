from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPalette
import pyqtgraph as qtg

from GUI.Viewer_3D_RT import *
from GUI.Viewer_DVH import *

class Viewer_Grid(QGridLayout):

  def __init__(self):
    QGridLayout.__init__(self)

    self.viewer_axial = Viewer_3D_RT("axial")
    self.viewer_coronal = Viewer_3D_RT("coronal")
    self.viewer_sagittal = Viewer_3D_RT("sagittal")
    self.viewer_DVH = Viewer_DVH()

    self.setColumnStretch(0, 1)
    self.setColumnStretch(1, 1)
    self.setRowStretch(0, 1)
    self.setRowStretch(1, 1)

    self.addWidget(self.viewer_axial, 0,0)
    self.addWidget(self.viewer_sagittal, 0,1)
    self.addWidget(self.viewer_coronal, 1,0)
    self.addWidget(self.viewer_DVH, 1,1)
  


  def clear_all(self):
    self.viewer_axial.clear_all()
    self.viewer_coronal.clear_all()
    self.viewer_sagittal.clear_all()
    self.viewer_DVH.clear_DVH()
  


  def update_all_views(self):
    self.viewer_axial.update_viewer()
    self.viewer_coronal.update_viewer()
    self.viewer_sagittal.update_viewer()
    self.viewer_DVH.update_DVH()



  def set_DVH(self, DVH_list):
    self.viewer_DVH.set_DVH_list(DVH_list)



  def set_DVHband(self, DVHband_list):
    self.viewer_DVH.set_DVHband_list(DVHband_list)    



  def clear_CT_images(self):
    self.viewer_axial.clear_CT_image()
    self.viewer_coronal.clear_CT_image()
    self.viewer_sagittal.clear_CT_image()



  def clear_Dose_images(self):
    self.viewer_axial.clear_Dose_image()
    self.viewer_coronal.clear_Dose_image()
    self.viewer_sagittal.clear_Dose_image()



  def clear_Contour_images(self):
    self.viewer_axial.clear_Contour_image()
    self.viewer_coronal.clear_Contour_image()
    self.viewer_sagittal.clear_Contour_image()



  def set_CT_images(self, CT_image, resolution):
    self.viewer_axial.set_CT_image(CT_image, resolution)
    self.viewer_coronal.set_CT_image(CT_image, resolution)
    self.viewer_sagittal.set_CT_image(CT_image, resolution)



  def set_Dose_images(self, Dose_image):
    self.viewer_axial.set_Dose_image(Dose_image)
    self.viewer_coronal.set_Dose_image(Dose_image)
    self.viewer_sagittal.set_Dose_image(Dose_image)



  def set_Contour_images(self, Contour_image):
    self.viewer_axial.set_Contour_image(Contour_image)
    self.viewer_coronal.set_Contour_image(Contour_image)
    self.viewer_sagittal.set_Contour_image(Contour_image)



  def Display_IsoCenter(self, isocenter):
    self.viewer_axial.set_IsoCenter(isocenter)
    self.viewer_coronal.set_IsoCenter(isocenter)
    self.viewer_sagittal.set_IsoCenter(isocenter)



  def Clear_IsoCenter(self):
    self.viewer_axial.Clear_IsoCenter()
    self.viewer_coronal.Clear_IsoCenter()
    self.viewer_sagittal.Clear_IsoCenter()



  def Display_Spots(self, spots):
    self.viewer_axial.set_Spots(spots)
    self.viewer_coronal.set_Spots(spots)
    self.viewer_sagittal.set_Spots(spots)



  def Clear_Spots(self):
    self.viewer_axial.Clear_Spots()
    self.viewer_coronal.Clear_Spots()
    self.viewer_sagittal.Clear_Spots()



  def scroll_viewers(self, numSteps):
    if(self.viewer_axial.underMouse()): self.viewer_axial.scroll_viewer(numSteps)
    elif(self.viewer_coronal.underMouse()): self.viewer_coronal.scroll_viewer(numSteps)
    elif(self.viewer_sagittal.underMouse()): self.viewer_sagittal.scroll_viewer(numSteps)
