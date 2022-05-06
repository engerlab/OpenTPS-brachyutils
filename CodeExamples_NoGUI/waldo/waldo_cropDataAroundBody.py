"""
This file contains an example on how to:
- Read a serialized patient with a Dynamic3DSequence, a Dynamic3DModel and an RTStruct
!! The data is not given in the test data folder of the project !!
- Select an ROI from the RTStruct object
- Get the ROI as an ROIMask
- Get the box around the ROI in scanner coordinates
- Crop the dynamic sequence and the dynamic model around the box
"""

import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)

from Core.Processing.ImageProcessing.crop3D import *
from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure

if __name__ == '__main__':

    organ = 'lung'
    patientFolder = 'Patient_8'
    patientComplement = '/1/FDG1'
    basePath = '/DATA2/public/'

    # resultFolder = '/test3/'
    # resultDataFolder = 'data/'

    bodyStructName = 'patient'
    dataName = 'dynModAndROIs.p'

    dataPath = basePath + organ  + '/' + patientFolder + patientComplement + '/' + dataName

    dataNameWithoutExtension = dataName.split('.')[0]
    # print(dataNameWithoutExtension)
    savingPath = basePath + organ  + '/' + patientFolder + patientComplement + '/' + dataNameWithoutExtension + '_bodyCropped'
    
    patient = loadDataStructure(dataPath)[0]
    # dynSeq = patient.getPatientDataOfType("Dynamic3DSequence")[0]
    dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct = patient.getPatientDataOfType("RTStruct")[0]

    ## get the ROI and mask on which we want to apply the motion signal
    print('Available ROIs')
    rtStruct.print_ROINames()
    bodyContour = rtStruct.getContourByName(bodyStructName)
    ROIMask = bodyContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)

    box = getBoxAroundROI(ROIMask)
    marginInMM = [10, 10, 10]
    print('-' * 50)
    crop3DDataAroundBox(dynMod, box, marginInMM=marginInMM)

    ## Save it as a serialized object
    saveSerializedObjects(patient, savingPath)