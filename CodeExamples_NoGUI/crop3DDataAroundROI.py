"""
This file contains an example on how to:
- Read a serialized patient with a Dynamic3DSequence, a Dynamic3DModel and an RTStruct
!! The data is not given in the test data folder of the project !!
- Select an ROI from the RTStruct object
- Get the ROI as an ROIMask
- Get the box around the ROI in scanner coordinates
- Crop the dynamic sequence and the dynamic model around the box
"""

from Core.Processing.ImageProcessing.crop3D import *
from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure

dataPath = '/home/damien/Desktop/Patient0/Patient0BaseAndMod_Velocity.p'
patient = loadDataStructure(dataPath)[0]

dynSeq = patient.getPatientDataOfType("Dynamic3DSequence")[0]
dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
rtStruct = patient.getPatientDataOfType("RTStruct")[0]

## get the ROI and mask on which we want to apply the motion signal
print('Available ROIs')
rtStruct.print_ROINames()
bodyContour = rtStruct.getContourByName('body')
ROIMask = bodyContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)

box = getBoxAroundROI(ROIMask)
marginInMM = 10
crop3DDataAroundBox(dynSeq, box, marginInMM=marginInMM)
print('-'*50)
crop3DDataAroundBox(dynMod, box, marginInMM=marginInMM)