
import os

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDir, pyqtSignal

class Toolbox_PatientData(QWidget):

  Current_CT_changed = pyqtSignal(int)
  Current_dose_changed = pyqtSignal(int)
  Current_plan_changed = pyqtSignal(int)
  Data_path_changed = pyqtSignal(str)
  ROI_list_changed = pyqtSignal()
  Viewer_display_spots = pyqtSignal(int)
  Viewer_clear_spots = pyqtSignal()
  New_CT_created = pyqtSignal(str)
  New_dose_created = pyqtSignal(str)
  CT_removed = pyqtSignal(int)
  CT_renamed = pyqtSignal(int, str)

  def __init__(self, PatientList, toolbox_width):
    QWidget.__init__(self)

    self.Patients = PatientList
    self.toolbox_width = toolbox_width
    self.data_path = QDir.currentPath()

    self.layout = QVBoxLayout()
    self.setLayout(self.layout)
    self.layout.addWidget(QLabel('<b>CT images:</b>'))
    self.CT_list = QListWidget()
    self.CT_list.currentRowChanged.connect(lambda row=self.CT_list.currentRow(): self.Current_CT_changed.emit(row))
    self.CT_list.setContextMenuPolicy(Qt.CustomContextMenu)
    self.CT_list.customContextMenuRequested.connect(lambda pos, list_type='CT': self.List_RightClick(pos, list_type))
    self.layout.addWidget(self.CT_list)
    self.layout.addSpacing(10)
    self.layout.addWidget(QLabel('<b>Dose distributions:</b>'))
    self.Dose_list = QListWidget()
    self.Dose_list.currentRowChanged.connect(lambda row=self.Dose_list.currentRow(): self.Current_dose_changed.emit(row))
    self.Dose_list.setContextMenuPolicy(Qt.CustomContextMenu)
    self.Dose_list.customContextMenuRequested.connect(lambda pos, list_type='dose': self.List_RightClick(pos, list_type))
    self.layout.addWidget(self.Dose_list)
    self.layout.addSpacing(10)
    self.layout.addWidget(QLabel('<b>Treatment plans:</b>'))
    self.Plan_list = QListWidget()
    self.Plan_list.currentRowChanged.connect(lambda row=self.Plan_list.currentRow(): self.Current_plan_changed.emit(row))
    self.Plan_list.setContextMenuPolicy(Qt.CustomContextMenu)
    self.Plan_list.customContextMenuRequested.connect(lambda pos, list_type='plan': self.List_RightClick(pos, list_type))
    self.layout.addWidget(self.Plan_list)
    self.layout.addSpacing(10)
    self.LoadButton = QPushButton('Load patient data')
    self.layout.addWidget(self.LoadButton)
    self.LoadButton.clicked.connect(self.load_patient_data) 


  def load_patient_data(self):
    self.data_path = QFileDialog.getExistingDirectory(self, "Open patient data folder", self.data_path)

    self.Data_path_changed.emit(self.data_path)

    self.Patients.list_dicom_files(self.data_path, 1)
    self.Patients.print_patient_list()
    self.Patients.list[0].import_patient_data()
    
    # display CT images
    for ct in self.Patients.list[0].CTimages:
      if(ct.isLoaded == 1):
        self.CT_list.addItem(ct.ImgName)
        self.New_CT_created.emit(ct.ImgName)
    self.CT_list.setCurrentRow(self.CT_list.count()-1)
    
    # display dose distributions
    for dose in self.Patients.list[0].RTdoses:
      if(dose.isLoaded == 1): 
        self.Dose_list.addItem(dose.ImgName)
        self.New_dose_created.emit(dose.ImgName)
    self.Dose_list.setCurrentRow(self.Dose_list.count()-1)
      
    # display plans
    for plan in self.Patients.list[0].Plans:
      if(plan.isLoaded == 1): 
        self.Plan_list.addItem(plan.PlanName)
    self.Plan_list.setCurrentRow(self.Plan_list.count()-1)

    # display contours
    self.ROI_list_changed.emit()



  def Add_CT(self, Name, Change_current_selection=0):
    # add dose to the list
    self.CT_list.addItem(Name)

    # display new dose
    if(Change_current_selection == 1):
      currentRow = self.CT_list.count()-1
      self.CT_list.setCurrentRow(currentRow)



  def Add_dose(self, Name):
    # add dose to the list
    self.Dose_list.addItem(Name)

    # display new dose
    currentRow = self.Dose_list.count()-1
    self.Dose_list.setCurrentRow(currentRow)



  def Add_plan(self, Name):
    # add dose to the list
    self.Plan_list.addItem(Name)

    # display new dose
    currentRow = self.Plan_list.count()-1
    self.Plan_list.setCurrentRow(currentRow)



  def List_RightClick(self, pos, list_type):
    if(list_type == 'CT'):
      item = self.CT_list.itemAt(pos)
      row = self.CT_list.row(item)
      pos = self.CT_list.mapToGlobal(pos)
   
    elif(list_type == 'dose'):
      item = self.Dose_list.itemAt(pos)
      row = self.Dose_list.row(item)
      pos = self.Dose_list.mapToGlobal(pos)
   
    elif(list_type == 'plan'):
      item = self.Plan_list.itemAt(pos)
      row = self.Plan_list.row(item)
      pos = self.Plan_list.mapToGlobal(pos)
      patient_id, plan_id = self.Patients.find_plan(row)
      plan = self.Patients.list[patient_id].Plans[plan_id]

    else: return
    
    if(row > -1):
      self.context_menu = QMenu()
      if(list_type == 'dose'):
        self.export_action = QAction("Export")
        self.export_action.triggered.connect(lambda checked, list_type=list_type, row=row: self.export_item(list_type, row))
        self.context_menu.addAction(self.export_action)
      
      self.rename_action = QAction("Rename")
      self.rename_action.triggered.connect(lambda checked, list_type=list_type, row=row: self.rename_item(list_type, row))
      self.context_menu.addAction(self.rename_action)
      
      self.delete_action = QAction("Delete")
      self.delete_action.triggered.connect(lambda checked, list_type=list_type, row=row: self.delete_item(list_type, row))
      self.context_menu.addAction(self.delete_action)
      
      if(list_type == 'plan'):
        if(plan.ScanMode == 'LINE'):
          self.convert_action = QAction("Convert line scanning to PBS plan")
          self.convert_action.triggered.connect(lambda checked: plan.convert_LineScanning_to_PBS())
          self.context_menu.addAction(self.convert_action)

        self.display_spot_action = []
        self.display_spot_action.append( QAction("Display spots (full plan)") )
        self.display_spot_action[0].triggered.connect(lambda checked, beam=-1: self.Viewer_display_spots.emit(beam))
        self.context_menu.addAction(self.display_spot_action[0])
        for b in range(len(plan.Beams)):
          self.display_spot_action.append( QAction("Display spots (Beam " + str(b+1) + ")") )
          self.display_spot_action[b+1].triggered.connect(lambda checked, beam=b: self.Viewer_display_spots.emit(beam))
          self.context_menu.addAction(self.display_spot_action[b+1])

        self.remove_spot_action = QAction("Remove displayed spots")
        self.remove_spot_action.triggered.connect(self.Viewer_clear_spots.emit)
        self.context_menu.addAction(self.remove_spot_action)
      
      self.context_menu.popup(pos)



  def rename_item(self, list_type, row):
    if(list_type == 'CT'):
      patient_id, ct_id = self.Patients.find_CT_image(row)
      NewName, okPressed = QInputDialog.getText(self, "Rename " + list_type + " image", "New name:", QLineEdit.Normal, self.Patients.list[patient_id].CTimages[ct_id].ImgName)
      if(okPressed):
        self.Patients.list[patient_id].CTimages[ct_id].ImgName = NewName
        self.CT_list.item(row).setText(NewName)
        self.CT_renamed.emit(row, NewName)
        
    elif(list_type == 'dose'):
      patient_id, dose_id = self.Patients.find_dose_image(row)
      NewName, okPressed = QInputDialog.getText(self, "Rename " + list_type + " image", "New name:", QLineEdit.Normal, self.Patients.list[patient_id].RTdoses[dose_id].ImgName)
      if(okPressed):
        self.Patients.list[patient_id].RTdoses[dose_id].ImgName = NewName
        self.Dose_list.item(row).setText(NewName)
        
    elif(list_type == 'plan'):
      patient_id, plan_id = self.Patients.find_plan(row)
      NewName, okPressed = QInputDialog.getText(self, "Rename " + list_type + " plan", "New name:", QLineEdit.Normal, self.Patients.list[patient_id].Plans[plan_id].PlanName)
      if(okPressed):
        self.Patients.list[patient_id].Plans[plan_id].PlanName = NewName
        self.Plan_list.item(row).setText(NewName)
        
        
    
  def delete_item(self, list_type, row):
    if(list_type == 'CT'):
      patient_id, ct_id = self.Patients.find_CT_image(row)
      DeleteReply = QMessageBox.question(self, 'Delete image', 'Delete "' + self.Patients.list[patient_id].CTimages[ct_id].ImgName + '" CT image ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
      if(DeleteReply == QMessageBox.Yes):
        del self.Patients.list[patient_id].CTimages[ct_id]
        self.CT_list.takeItem(row)
        self.CT_removed.emit(row)
        
    elif(list_type == 'dose'):
      patient_id, dose_id = self.Patients.find_dose_image(row)
      DeleteReply = QMessageBox.question(self, 'Delete image', 'Delete "' + self.Patients.list[patient_id].RTdoses[dose_id].ImgName + '" dose image ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
      if(DeleteReply == QMessageBox.Yes):
        del self.Patients.list[patient_id].RTdoses[dose_id]
        self.Dose_list.takeItem(row)
        
    elif(list_type == 'plan'):
      patient_id, plan_id = self.Patients.find_plan(row)
      DeleteReply = QMessageBox.question(self, 'Delete plan', 'Delete "' + self.Patients.list[patient_id].Plans[plan_id].PlanName + '" plan ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
      if(DeleteReply == QMessageBox.Yes):
        del self.Patients.list[patient_id].Plans[plan_id]
        self.Plan_list.takeItem(row)



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