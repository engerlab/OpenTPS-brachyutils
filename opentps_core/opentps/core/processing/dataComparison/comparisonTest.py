from opentps.core.processing.dataComparison.dynamic3DModelComparison import compareModels
from opentps.core.io.serializedObjectIO import loadDataStructure

organ = 'lung'
study = 'FDGorFAZA_study'
patientFolder = 'Patient_6'
basePath = '/data/WalBan/'#'/DATA2/public/'
dataName = 'dynModAndROIs.p'
dataName1 = 'dynModAndROIs_Patient6_FDG_1.p'
dataName2 = 'dynModAndROIs_Patient6_FDG_2.p'
#pour le patient 12, il faut changer l'ordre chronologique car le masque au temps 1 est plus petit qu'au temps 2
patientComplement1 = '/1/FDG1'
patientComplement2 = '/2/FDG2'
targetContourToUse1 = 'gtv t'#'GTVp'
targetContourToUse2 = 'gtv t'#'gtv t'

dataPath1 = basePath + organ + '/' + study + '/' + patientFolder + patientComplement1 + '/' + dataName1
dataPath2 = basePath + organ + '/' + study + '/' + patientFolder + patientComplement2 + '/' + dataName2

model1 = loadDataStructure(dataPath1)[0]
model2 = loadDataStructure(dataPath2)[0]
compareModels(model1, model2, targetContourToUse1, targetContourToUse2)