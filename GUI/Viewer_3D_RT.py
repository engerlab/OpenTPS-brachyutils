from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPalette, QPen

import numpy as np

class Viewer_3D_RT(QLabel):

  def __init__(self, view_direction):
    QLabel.__init__(self, "No image loaded")

    self.Viewer_initialized = 0
    self.view_direction = view_direction
    self.CT_image = np.array([])
    self.Dose_image = np.array([])
    self.Contour_image = np.array([])
    self.IsoCenter = []
    self.Spots = []
    self.current_slice = 0
    self.resolution = [1,1,1]
    self.GridSize = [0, 0, 0]

    self.viewer_palette = QPalette()
    self.viewer_palette.setColor(QPalette.Window, Qt.black)

    self.setAlignment(Qt.AlignCenter)
    self.setAutoFillBackground(True)
    self.setPalette(self.viewer_palette)



  def clear_all(self):
    self.Viewer_initialized = 0
    self.CT_image = np.array([])
    self.Dose_image = np.array([])
    self.Contour_image = np.array([])
    self.IsoCenter = []
    self.Spots = []
    self.current_slice = 0
    self.resolution = [1,1,1]
    self.GridSize = [0, 0, 0]
    self.update_viewer()



  def clear_CT_image(self):
    self.Viewer_initialized = 0
    self.CT_image = np.array([])
    self.resolution = [1,1,1]
    self.GridSize = [0, 0, 0]
    self.update_viewer()



  def clear_Dose_image(self):
    self.Dose_image = np.array([])
    self.update_viewer()



  def clear_Contour_image(self):
    self.Contour_image = np.array([])
    self.update_viewer()



  def set_CT_image(self, CT_image, resolution):
    self.CT_image = CT_image
    self.resolution = resolution
    self.GridSize = list(self.CT_image.shape)

    if(self.view_direction == 'axial'): self.current_slice = round(self.GridSize[2] / 2)
    elif(self.view_direction == 'sagittal'): self.current_slice = round(self.GridSize[0] / 2)
    else: self.current_slice = round(self.GridSize[1] / 2)

    self.Viewer_initialized = 1  
    self.update_viewer()



  def set_Dose_image(self, Dose_image):
    self.Dose_image = Dose_image
    self.update_viewer()



  def set_Contour_image(self, Contour_image):
    self.Contour_image = Contour_image
    self.update_viewer()



  def set_IsoCenter(self, isocenter):
    self.IsoCenter = isocenter
    self.update_viewer()



  def Clear_IsoCenter(self):
    self.IsoCenter = []
    self.update_viewer()



  def set_Spots(self, spots):
    self.Spots = spots
    self.update_viewer()



  def Clear_Spots(self):
    self.Spots = []
    self.update_viewer()



  def scroll_viewer(self, numSteps):
    if(self.Viewer_initialized == 0): return

    self.current_slice += numSteps 
    if(self.current_slice < 0): self.current_slice = 0
    if(self.view_direction == 'axial' and self.current_slice > self.GridSize[2]-1): self.current_slice = self.GridSize[2] - 1
    if(self.view_direction == 'coronal' and self.current_slice > self.GridSize[0]-1): self.current_slice = self.GridSize[0] - 1
    if(self.view_direction == 'sagittal' and self.current_slice > self.GridSize[1]-1): self.current_slice = self.GridSize[1] - 1
    self.update_viewer()
        
        
    
  def update_viewer(self):
    if(self.Viewer_initialized == 0):
      return
      
    # calculate scaling factor
    if(self.view_direction == 'axial'): Yscaling = self.resolution[1] / self.resolution[0]
    elif(self.view_direction == 'sagittal'): Yscaling = self.resolution[2] / self.resolution[1]
    else: Yscaling = self.resolution[2] / self.resolution[0]
            
    # paint CT image
    if(self.view_direction == 'axial'): img_data = self.CT_image[:,:,round(self.current_slice)]
    elif(self.view_direction == 'sagittal'): img_data = np.flip(np.transpose(self.CT_image[:,round(self.current_slice),:], (1,0)), 0)
    else: img_data = np.flip(np.transpose(self.CT_image[round(self.current_slice),:,:], (1,0)), 0)
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
    if(self.Dose_image != []):
      if(self.view_direction == 'axial'): img_data = self.Dose_image[:,:,round(self.current_slice)]
      elif(self.view_direction == 'sagittal'): img_data = np.flip(np.transpose(self.Dose_image[:,round(self.current_slice),:], (1,0,2)), 0)
      else: img_data = np.flip(np.transpose(self.Dose_image[round(self.current_slice),:,:], (1,0,2)), 0)
      img_data = np.require(img_data, np.uint8, 'C')
      DoseImage = QImage(img_data, img_size[1], img_size[0], QImage.Format_ARGB32)
      painter.setOpacity(0.3)
      painter.drawImage(0, 0, DoseImage)
      painter.setOpacity(1.0)
      
    # draw spot positions
    if(self.Spots != []):
      pen = QPen(Qt.blue)
      pen.setWidthF(1.0)
      painter.setPen(pen)
      for spot in self.Spots:
        if(self.view_direction == 'axial'): 
          if(round(self.current_slice) != round(spot[2])): continue
          SpotPosition = QPointF(spot[0], spot[1])
        elif(self.view_direction == 'sagittal'): 
          if(round(self.current_slice) != round(spot[0])): continue
          SpotPosition = QPointF(spot[1], img_size[0]-spot[2])
        else: 
          if(round(self.current_slice) != round(spot[1])): continue
          SpotPosition = QPointF(spot[0], img_size[0]-spot[2])
        painter.drawPoint(SpotPosition)
    
    # paint contour image
    if(self.Contour_image != []):
      if(self.view_direction == 'axial'): img_data = self.Contour_image[:,:,round(self.current_slice)]
      elif(self.view_direction == 'sagittal'): img_data = np.flip(np.transpose(self.Contour_image[:,round(self.current_slice),:], (1,0,2)), 0)
      else: img_data = np.flip(np.transpose(self.Contour_image[round(self.current_slice),:,:], (1,0,2)), 0)
      img_data = np.require(img_data, np.uint8, 'C')
      ContourImage = QImage(img_data, img_size[1], img_size[0], QImage.Format_ARGB32)
      painter.drawImage(0, 0, ContourImage)
      
    # draw plan iso-center
    if(self.IsoCenter != []):
      if(self.view_direction == 'axial'): IsoCenter2D = QPointF(self.IsoCenter[0], self.IsoCenter[1])
      elif(self.view_direction == 'sagittal'): IsoCenter2D = QPointF(self.IsoCenter[1], img_size[0]-self.IsoCenter[2])
      else: IsoCenter2D = QPointF(self.IsoCenter[0], img_size[0]-self.IsoCenter[2])
      pen = QPen(Qt.red)
      pen.setWidthF(3.0)
      painter.setPen(pen)
      painter.drawPoint(IsoCenter2D)
    
    painter.end()
    
    # resize image to window scale and display
    if(self.width()/img_size[1] < self.height()/(Yscaling*img_size[0])):
      self.setPixmap(QPixmap.fromImage(MergedImage).scaledToWidth(self.width()-10, mode=Qt.SmoothTransformation))
    else:
      self.setPixmap(QPixmap.fromImage(MergedImage).scaledToHeight(self.height()-10, mode=Qt.SmoothTransformation))
    

