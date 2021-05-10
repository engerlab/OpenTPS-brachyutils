from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal

from Process.Registration import *

class Toolbox_ImageRegistration(QWidget):

  Registration_updated = pyqtSignal()
  New_CT_created = pyqtSignal(str)

  def __init__(self, PatientList, toolbox_width):
    QWidget.__init__(self)

    self.Patients = PatientList
    self.toolbox_width = toolbox_width
    self.diff_image_viewer = []
    self.ROI_box_viewer = []
    self.PixelSpacing_viewer = [1, 1, 1]

    self.layout = QVBoxLayout()
    self.setLayout(self.layout)
    self.layout.addWidget(QLabel('<b>Fixed image:</b>'))
    self.Fixed = QComboBox()
    self.Fixed.setMaximumWidth(self.toolbox_width-18)
    self.layout.addWidget(self.Fixed)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Moving image:</b>'))
    self.Moving = QComboBox()
    self.Moving.setMaximumWidth(self.toolbox_width-18)
    self.layout.addWidget(self.Moving)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Registration algorithm:</b>'))
    self.Algorithm = QComboBox()
    self.Algorithm.addItem("Quick translation search")
    self.Algorithm.addItem("Rigid registration")
    self.Algorithm.addItem("Deformable registration (Demons)")
    self.Algorithm.setMaximumWidth(self.toolbox_width-18)
    self.layout.addWidget(self.Algorithm)
    self.layout.addSpacing(15)
    self.layout.addWidget(QLabel('<b>Region of Interest:</b>'))
    self.ROI = QComboBox()
    self.ROI.addItem("Entire image")
    self.ROI.setMaximumWidth(self.toolbox_width-18)
    self.layout.addWidget(self.ROI)
    self.layout.addSpacing(30)
    self.RegisterButton = QPushButton('Register')
    self.layout.addWidget(self.RegisterButton)
    self.RegisterButton.clicked.connect(self.register_images)
    self.layout.addSpacing(15)
    self.ResampleButton = QPushButton('Resample moving image')
    self.layout.addWidget(self.ResampleButton)
    self.ResampleButton.clicked.connect(self.resample_moving)
    self.layout.addStretch()
    self.Fixed.currentIndexChanged.connect(self.recompute_image_difference)
    self.Moving.currentIndexChanged.connect(self.recompute_image_difference)
    self.ROI.currentIndexChanged.connect(self.display_registration_ROI)



  def Add_CT(self, Name):
    # add dose to the list
    self.Fixed.addItem(Name)
    self.Moving.addItem(Name)



  def Remove_CT(self, row):
    self.Fixed.removeItem(row)
    self.Moving.removeItem(row)



  def Rename_CT(self, row, NewName):
    self.Fixed.setItemText(row,NewName)
    self.Moving.setItemText(row,NewName)



  def Add_new_contour(self, ROIName):
    self.ROI.addItem(ROIName)



  def Remove_contour(self, ID):
    self.ROI.removeItem(ID+1)



  def register_images(self):
    Fixed_id = self.Fixed.currentIndex()
    Moving_id = self.Moving.currentIndex()
    if(Fixed_id < 0 or Moving_id < 0): return

    ct_patient_id, ct_id = self.Patients.find_CT_image(Fixed_id)
    fixed = self.Patients.list[ct_patient_id].CTimages[ct_id]
    ct_patient_id, ct_id = self.Patients.find_CT_image(Moving_id)
    moving = self.Patients.list[ct_patient_id].CTimages[ct_id]

    reg = Registration(fixed, moving)

    if(self.ROI.currentText() != "Entire image"):
      patient_id, struct_id, contour_id = self.Patients.find_contour(self.ROI.currentText())
      ROI = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
      reg.setROI(ROI)

    if(self.Algorithm.currentText() == "Quick translation search"):
      translation = reg.Quick_translation_search()
      print(translation)
      reg.Translate_origin(moving, translation)

    elif(self.Algorithm.currentText() == "Rigid registration"):
      translation = reg.Rigid_registration()
      print(translation)
      reg.Translate_origin(moving, translation)
      
    elif(self.Algorithm.currentText() == "Deformable registration (Demons)"):
      DefField = reg.Registration_demons()
      reg.Deformed.ImgName += "_deformed"
      self.Patients.list[ct_patient_id].CTimages.append(reg.Deformed)
      self.New_CT_created.emit(reg.Deformed.ImgName)
      self.Fixed.addItem(reg.Deformed.ImgName)
      self.Moving.addItem(reg.Deformed.ImgName)
      self.Moving.setCurrentIndex(self.Moving.count()-1)

    self.recompute_image_difference()



  def resample_moving(self):
    Fixed_id = self.Fixed.currentIndex()
    Moving_id = self.Moving.currentIndex()
    if(Fixed_id < 0 or Moving_id < 0): return

    ct_patient_id, ct_id = self.Patients.find_CT_image(Fixed_id)
    fixed = self.Patients.list[ct_patient_id].CTimages[ct_id]
    ct_patient_id, ct_id = self.Patients.find_CT_image(Moving_id)
    moving = self.Patients.list[ct_patient_id].CTimages[ct_id]

    reg = Registration(fixed, moving)
    resampled = reg.Resample_moving_image(KeepFixedShape=True)
    resampled.ImgName += "_registered"

    self.Patients.list[ct_patient_id].CTimages.append(resampled)
    self.New_CT_created.emit(resampled.ImgName)
    self.Fixed.addItem(resampled.ImgName)
    self.Moving.addItem(resampled.ImgName)



  def recompute_image_difference(self):
    Fixed_id = self.Fixed.currentIndex()
    Moving_id = self.Moving.currentIndex()
    if(Fixed_id < 0 or Moving_id < 0): return

    if(Fixed_id == Moving_id): return

    ct_patient_id, ct_id = self.Patients.find_CT_image(Fixed_id)
    fixed = self.Patients.list[ct_patient_id].CTimages[ct_id]
    ct_patient_id, ct_id = self.Patients.find_CT_image(Moving_id)
    moving = self.Patients.list[ct_patient_id].CTimages[ct_id]

    reg = Registration(fixed, moving)
    diff = reg.Image_difference(KeepFixedShape=False)
    self.diff_image_viewer = diff.prepare_image_for_viewer()
    self.PixelSpacing_viewer = diff.PixelSpacing

    self.display_registration_ROI()
    self.Registration_updated.emit()



  def display_registration_ROI(self):
    if(self.ROI.currentText() == "Entire image" or self.diff_image_viewer == []):
      self.ROI_box_viewer = []
    else:
      # compute ROI box shape
      patient_id, struct_id, contour_id = self.Patients.find_contour(self.ROI.currentText())
      ROI = self.Patients.list[patient_id].RTstructs[struct_id].Contours[contour_id]
      reg = Registration()
      reg.setROI(ROI)
      start = reg.ROI_box[0]
      stop = reg.ROI_box[1]

      # display
      img_size = list(self.diff_image_viewer.shape)
      self.ROI_box_viewer = np.zeros((img_size[0], img_size[1], img_size[2], 4))
      self.ROI_box_viewer[:,:,:,2] = 255
      self.ROI_box_viewer[start[0]:stop[0], start[1]:stop[1], start[2]:stop[2], 3] = 255
      self.ROI_box_viewer[start[0]+1:stop[0]-1, start[1]+1:stop[1]-1, start[2]+1:stop[2]-1, 3] = 0

    self.Registration_updated.emit()