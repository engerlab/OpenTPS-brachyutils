import os
import pydicom

from Process.CTimage import *
from Process.RTdose import *
from Process.RTplan import *
from Process.RTstruct import *

class PatientList:

  def __init__(self):
    self.list = []
    
    
  
  def find_CT_image(self, display_id):
    count = -1
    for patient_id in range(len(self.list)):
      for ct_id in range(len(self.list[patient_id].CTimages)):
        if(self.list[patient_id].CTimages[ct_id].isLoaded == 1): count += 1
        if(count == display_id): break
      if(count == display_id): break
      
    return patient_id, ct_id
    
    
  
  def find_dose_image(self, display_id):
    count = -1
    for patient_id in range(len(self.list)):
      for dose_id in range(len(self.list[patient_id].RTdoses)):
        if(self.list[patient_id].RTdoses[dose_id].isLoaded == 1): count += 1
        if(count == display_id): break
      if(count == display_id): break
      
    return patient_id, dose_id
    
    
  
  def find_plan(self, display_id):
    count = -1
    for patient_id in range(len(self.list)):
      for plan_id in range(len(self.list[patient_id].Plans)):
        if(self.list[patient_id].Plans[plan_id].isLoaded == 1): count += 1
        if(count == display_id): break
      if(count == display_id): break
      
    return patient_id, plan_id
    
    
  
  def find_contour(self, ROIName):
    for patient_id in range(len(self.list)):
      for struct_id in range(len(self.list[patient_id].RTstructs)):
        if(self.list[patient_id].RTstructs[struct_id].isLoaded == 1):
          for contour_id in range(len(self.list[patient_id].RTstructs[struct_id].Contours)):
            if(self.list[patient_id].RTstructs[struct_id].Contours[contour_id].ROIName == ROIName):
              return patient_id, struct_id, contour_id
    
    
    
  def list_dicom_files(self, folder_path, recursive):
    file_list = os.listdir(folder_path)
    
    for file_name in file_list:
      file_path = os.path.join(folder_path, file_name)
      
      # folders
      if os.path.isdir(file_path):
        if recursive == True:
          subfolder_list = self.list_dicom_files(file_path, True)
          #join_patient_lists(Patients, subfolder_list)
          
      # files
      elif os.path.isfile(file_path):
      
        try:
          dcm = pydicom.dcmread(file_path)
        except:
          print("Invalid Dicom file: " + file_path)
          continue
        
        patient_id = next((x for x, val in enumerate(self.list) if val.PatientInfo.PatientID == dcm.PatientID), -1)

        # print(dcm.dir('UID'))
        # print("PatientID: " + dcm.PatientID) # user defined patient ID
        # print("StudyID: " + dcm.StudyID) # user defined study ID
        # print("SeriesInstanceUID: " + dcm.SeriesInstanceUID) # series UID
        # print("StudyInstanceUID: " + dcm.StudyInstanceUID) # study UID
        # print("SOPInstanceUID: " + dcm.SOPInstanceUID) # CT slice UID
        
        if patient_id == -1:
          Patient = PatientData()
          Patient.PatientInfo.PatientID = dcm.PatientID
          Patient.PatientInfo.PatientName = str(dcm.PatientName)
          Patient.PatientInfo.PatientBirthDate = dcm.PatientBirthDate
          Patient.PatientInfo.PatientSex = dcm.PatientSex
          self.list.append(Patient)
          patient_id = len(self.list) - 1

        # Dicom CT
        if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.2":
          ct_id = next((x for x, val in enumerate(self.list[patient_id].CTimages) if val.SeriesInstanceUID == dcm.SeriesInstanceUID), -1)
          if ct_id == -1:
            CT = CTimage()
            CT.SeriesInstanceUID = dcm.SeriesInstanceUID
            CT.PatientInfo = self.list[patient_id].PatientInfo
            CT.StudyInfo = StudyInfo()
            CT.StudyInfo.StudyInstanceUID = dcm.StudyInstanceUID
            CT.StudyInfo.StudyID = dcm.StudyID
            CT.StudyInfo.StudyDate = dcm.StudyDate
            CT.StudyInfo.StudyTime = dcm.StudyTime
            if(hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""): CT.ImgName = dcm.SeriesDescription
            else: CT.ImgName = dcm.SeriesInstanceUID
            self.list[patient_id].CTimages.append(CT)
            ct_id = len(self.list[patient_id].CTimages) - 1

          self.list[patient_id].CTimages[ct_id].DcmFiles.append(file_path)

        # Dicom dose
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.2":
          dose_id = next((x for x, val in enumerate(self.list[patient_id].RTdoses) if val.SOPInstanceUID == dcm.SOPInstanceUID), -1)
          if dose_id == -1:
            dose = RTdose()
            dose.SOPInstanceUID = dcm.SOPInstanceUID
            dose.SeriesInstanceUID = dcm.SeriesInstanceUID
            dose.PatientInfo = self.list[patient_id].PatientInfo
            dose.StudyInfo = StudyInfo()
            dose.StudyInfo.StudyInstanceUID = dcm.StudyInstanceUID
            dose.StudyInfo.StudyID = dcm.StudyID
            dose.StudyInfo.StudyDate = dcm.StudyDate
            dose.StudyInfo.StudyTime = dcm.StudyTime
            if(hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""): dose.ImgName = dcm.SeriesDescription
            else: dose.ImgName = dcm.SeriesInstanceUID
            dose.DcmFile = file_path
            self.list[patient_id].RTdoses.append(dose)

        # Dicom plan
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.5" or dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.8":
          plan_id = next((x for x, val in enumerate(self.list[patient_id].Plans) if val.SeriesInstanceUID == dcm.SeriesInstanceUID), -1)
          if plan_id == -1:
            plan = RTplan()
            plan.SeriesInstanceUID = dcm.SeriesInstanceUID
            plan.PatientInfo = self.list[patient_id].PatientInfo
            plan.StudyInfo = StudyInfo()
            plan.StudyInfo.StudyInstanceUID = dcm.StudyInstanceUID
            plan.StudyInfo.StudyID = dcm.StudyID
            plan.StudyInfo.StudyDate = dcm.StudyDate
            plan.StudyInfo.StudyTime = dcm.StudyTime
            if(hasattr(dcm, 'SeriesDescription') and dcm.SeriesDescription != ""): plan.PlanName = dcm.SeriesDescription
            else: plan.PlanName = dcm.SeriesInstanceUID
            plan.DcmFile = file_path
            self.list[patient_id].Plans.append(plan)

        # Dicom struct
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.3":
          struct_id = next((x for x, val in enumerate(self.list[patient_id].RTstructs) if val.SeriesInstanceUID == dcm.SeriesInstanceUID), -1)
          if struct_id == -1:
            struct = RTstruct()
            struct.SeriesInstanceUID = dcm.SeriesInstanceUID
            struct.PatientInfo = self.list[patient_id].PatientInfo
            struct.StudyInfo = StudyInfo()
            struct.StudyInfo.StudyInstanceUID = dcm.StudyInstanceUID
            struct.StudyInfo.StudyID = dcm.StudyID
            struct.StudyInfo.StudyDate = dcm.StudyDate
            struct.StudyInfo.StudyTime = dcm.StudyTime
            struct.DcmFile = file_path
            self.list[patient_id].RTstructs.append(struct)

        else:
          print("Unknown SOPClassUID " + dcm.SOPClassUID + " for file " + file_path)

      # other
      else:
        print("Unknown file type " + file_path)


  def print_patient_list(self):
    print("")
    for patient in self.list:
      patient.print_patient_info()

    print("")



class PatientData:

  def __init__(self):
    self.PatientInfo = PatientInfo()
    self.CTimages = []
    self.RTdoses = []
    self.Plans = []
    self.RTstructs = []
    
  def print_patient_info(self, prefix=""):
    print("")
    print(prefix + "PatientName: " + self.PatientInfo.PatientName)
    print(prefix+ "PatientID: " + self.PatientInfo.PatientID)
    
    for ct in self.CTimages:
      print("")
      ct.print_CT_info(prefix + "   ")

    print("")
    for dose in self.RTdoses:
      print("")
      dose.print_dose_info(prefix + "   ")

    print("")
    for plan in self.Plans:
      print("")
      plan.print_plan_info(prefix + "   ")

    print("")
    for struct in self.RTstructs:
      print("")
      struct.print_struct_info(prefix + "   ")
    
    

  def import_patient_data(self):
    # import CT images
    print("Import CT images")
    for ct in self.CTimages:
      if(ct.isLoaded == 1): continue
      ct.import_Dicom_CT()

    # import dose distributions
    print("Import dose images")
    for dose in self.RTdoses:
      if(dose.isLoaded == 1): continue
      dose.import_Dicom_dose(self.CTimages[0]) # to be improved: user select CT image

    # import plans
    print("Import treatment plans")
    for plan in self.Plans:
      if(plan.isLoaded == 1): continue
      plan.import_Dicom_plan()

    # import RTstructs
    print("Import RT-Structs")
    for struct in self.RTstructs:
      struct.import_Dicom_struct(self.CTimages[0]) # to be improved: user select CT image





class PatientInfo:

  def __init__(self):
    self.PatientID = ''
    self.PatientName = ''
    self.PatientBirthDate = ''
    self.PatientSex = ''




class StudyInfo:

  def __init__(self):
    self.StudyInstanceUID = ''
    self.StudyID = ''
    self.StudyDate = ''
    self.StudyTime = ''