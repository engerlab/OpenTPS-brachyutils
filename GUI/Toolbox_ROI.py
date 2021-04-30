from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QPixmap, QIcon

class Toolbox_ROI(QWidget):

  Current_contours_changed = pyqtSignal()
  New_contour_added = pyqtSignal(str)
  Contour_removed = pyqtSignal(int)

  def __init__(self, PatientList, toolbox_width):
    QWidget.__init__(self)

    self.Patients = PatientList
    self.toolbox_width = toolbox_width
    self.ROI_CheckBox = []
    self.CT_disp_ID = -1

    self.layout = QVBoxLayout()
    self.setLayout(self.layout)
    self.layout.addWidget(QLabel("No ROI loaded"))



  def Current_contours_changed_emit(self):
    self.Current_contours_changed.emit()



  def reload_ROI_list(self):

    # remove all contours from the list
    self.ROI_CheckBox = []
    while(self.layout.count() != 0):
      item = self.layout.takeAt(0).widget()
      if(item != None): 
        self.Contour_removed.emit(0)
        item.setParent(None)   

    # display list of contours in the GUI
    patient_id, ct_id = self.Patients.find_CT_image(self.CT_disp_ID)
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
        self.ROI_CheckBox[-1].stateChanged.connect(self.Current_contours_changed_emit) 
        self.layout.addWidget(self.ROI_CheckBox[-1])
        self.New_contour_added.emit(contour.ROIName)
        #self.toolbox_5_Target.addItem(contour.ROIName)
        #self.toolbox_6_Target.addItem(contour.ROIName)
        #self.toolbox_7_ROI.addItem(contour.ROIName)
        
    self.layout.addStretch()
    self.Current_contours_changed_emit()


