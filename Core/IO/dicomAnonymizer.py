from Core.IO.dataLoader import listAllFiles
import pydicom

def anonymiseDicom(dataPath, patientName):

    """
    Basic dicom anonymizer without options except to specify the new patient name
    The dicom file is replaced by the anonymised one ! Be careful if you want to keep the original you need a copy ;)
    """

    filesList = listAllFiles(dataPath)
    print(len(filesList["Dicom"]), 'dicom files found in the folder')

    for file in filesList["Dicom"]:
        print(file)
        dcm = pydicom.dcmread(file)

        dcm.PatientName = patientName
        dcm.InstanceCreationDate = '31012020'
        dcm.InstanceCreationTime = '31012020'
        dcm.StudyDate = '31012020'
        dcm.SeriesDate = '31012020'
        dcm.AcquisitionDate = '31012020'
        dcm.StudyTime = '31012020'
        dcm.SeriesTime = '31012020'
        dcm.ReferringPhysicianName = 'Doctor Who ?'
        dcm.PatientID = patientName
        dcm.PatientBirthDate = '31012020'
        dcm.PatientSex = 'Helicopter'
        dcm.OtherPatientNames = ''
        dcm.OperatorsName = ''
        dcm.StructureSetLabel = 'RTSTRUCT'
        dcm.StructureSetDate = '31012020'
        dcm.StructureSetTime = '31012020'

        pydicom.dcmwrite(file, dcm)


## ------------------------------------------------------------------------------------------------------
