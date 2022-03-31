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
import matplotlib.pyplot as plt

dataPath = '/home/damien/Desktop/Patient0/Patient0BaseAndMod_Displacement.p'
patient = loadDataStructure(dataPath)[0]

dynSeq = patient.getPatientDataOfType("Dynamic3DSequence")[0]
dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
rtStruct = patient.getPatientDataOfType("RTStruct")[0]

## get the ROI and mask on which we want to apply the motion signal
print('Available ROIs')
rtStruct.print_ROINames()
bodyContour = rtStruct.get_contour_by_name('MidP CT GTV')
ROIMask = bodyContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)

box = getBoxAroundROI(ROIMask)
marginInMM = [0, 10, 30]
crop3DDataAroundBox(dynSeq, box, marginInMM=marginInMM)
crop3DDataAroundBox(dynMod, box, marginInMM=marginInMM)

plt.figure()
plt.imshow(dynMod.midp.imageArray[:, :, 40])
plt.show()

savingPath = '/home/damien/Desktop/' + 'Test_dynModAndROIs_gtvCropped'
# dynMod.patient = None
# rtStruct.patient = None
saveSerializedObjects(patient, savingPath)