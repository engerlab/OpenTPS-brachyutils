from opentps.core.processing.dataComparison.dynamic3DModelComparison import compareModels
from opentps.core.io.serializedObjectIO import loadDataStructure

organ = 'lung'
study = 'FDGorFAZA_study'
patientFolder = 'Patient_12'
basePath = '/data/WalBan/'
dataName = 'dynModAndROIs.p'
patientComplement1 = '/1/FDG1'
patientComplement2 = '/2/FDG2'
targetContourToUse1 = 'gtv t'
targetContourToUse2 = 'GTVp'

dataPath1 = basePath + organ + '/' + study + '/' + patientFolder + patientComplement1 + '/' + dataName
dataPath2 = basePath + organ + '/' + study + '/' + patientFolder + patientComplement2 + '/' + dataName

model1 = loadDataStructure(dataPath1)[0]
model2 = loadDataStructure(dataPath2)[0]
compareModels(model1,model2)