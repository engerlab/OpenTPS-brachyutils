from Core.IO.dicomAnonymizer import anonymiseDicom

## ------------------------------------------------------------------------------------------------------
patientIndex = 15
patientName = 'Patient_' + str(patientIndex)

dataPath = "/media/damien/Dam2/Lung_Dario/" + str(patientIndex)

anonymiseDicom(dataPath, patientName)