from opentps.core.processing.dataComparison.dynamic3DModelComparison import compareModels
from opentps.core.io.serializedObjectIO import loadDataStructure

organ = 'lung'
study = 'FDGorFAZA_study'
patientFolder = 'Patient_12'#'Patient_12'
basePath = '/DATA2/public/'#'/data/WalBan/'
dataName = 'dynModAndROIs.p'
#pour le patient 12, il faut changer l'ordre chronologique car le masque au temps 1 est plus petit qu'au temps 2
patientComplement1 = '/2/FDG2'
patientComplement2 = '/1/FDG1'
targetContourToUse1 = 'GTVp'
targetContourToUse2 = 'gtv t'#'GTVp'

dataPath1 = basePath + organ + '/' + study + '/' + patientFolder + patientComplement1 + '/' + dataName
dataPath2 = basePath + organ + '/' + study + '/' + patientFolder + patientComplement2 + '/' + dataName

model1 = loadDataStructure(dataPath1)[0]
model2 = loadDataStructure(dataPath2)[0]
compareModels(model1, model2, targetContourToUse1, targetContourToUse2)