from Core.IO.dicomReader import readDicomCT
from Core.IO.dataLoader import listAllFiles
import pydicom

patientName = 'Patient0'

dataPath = "/home/damien/Desktop/" + patientName

filesList = listAllFiles(dataPath)
print(filesList)
print(len(filesList))

for file in filesList["Dicom"]:
    print(file)
    dcm = pydicom.dcmread(file)
    dcm.PatientName = patientName
    pydicom.dcmwrite(file, dcm)
    print(dcm.PatientName)

# Dicom field
# if dcm.SOPClassUID

#image1 = readDicomCT(filesList['Dicom'])
#print(image1)