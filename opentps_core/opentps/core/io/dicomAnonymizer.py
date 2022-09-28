from opentps.core.io.dataLoader import listAllFiles
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
        dcm.InstanceCreationDate = '01022010'
        dcm.InstanceCreationTime = '01022010'
        dcm.StudyDate = '01022010'
        dcm.SeriesDate = '01022010'
        dcm.AcquisitionDate = '01022010'
        dcm.StudyTime = '01022010'
        dcm.SeriesTime = '01022010'
        dcm.ReferringPhysicianName = 'Doctor Who ?'
        dcm.PatientID = patientName
        dcm.PatientBirthDate = '01022010'
        dcm.PatientSex = 'Helicopter'
        dcm.OtherPatientNames = ''
        dcm.OperatorsName = ''
        dcm.StructureSetLabel = 'RTSTRUCT'
        dcm.StructureSetDate = '01022010'
        dcm.StructureSetTime = '01022010'

        pydicom.dcmwrite(file, dcm)


## ------------------------------------------------------------------------------------------------------
