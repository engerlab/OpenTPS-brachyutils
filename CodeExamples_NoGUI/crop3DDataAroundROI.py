from Core.Processing.ImageProcessing.crop3D import *
from Core.IO.serializedObjectIO import saveSerializedObjects, loadDataStructure

dataPath = '/home/damien/Desktop/Patient0/Patient0BaseAndMod_Velocity.p'
# dataPath = '/home/damien/Desktop/Patient0/Patient0BaseAndMod.p'
patient = loadDataStructure(dataPath)[0]

dynSeq = patient.getPatientDataOfType("Dynamic3DSequence")[0]
dynMod = patient.getPatientDataOfType("Dynamic3DModel")[0]
rtStruct = patient.getPatientDataOfType("RTStruct")[0]

## get the ROI and mask on which we want to apply the motion signal
print('Available ROIs')
rtStruct.print_ROINames()
gtvContour = rtStruct.get_contour_by_name('body')
ROIMask = gtvContour.getBinaryMask(origin=dynMod.midp.origin, gridSize=dynMod.midp.gridSize, spacing=dynMod.midp.spacing)

box = getBoxAroundROI(ROIMask)
marginInMM = 10
crop3DDataAroundBox(dynSeq, box, marginInMM=marginInMM)
print('outside function', dynSeq.dyn3DImageList[0].origin, dynSeq.dyn3DImageList[0].gridSize)
print('-'*50)
crop3DDataAroundBox(dynMod, box, marginInMM=marginInMM)

savingPath = '/home/damien/Desktop/Patient0/Patient0BaseAndMod_Velocity_bodyCropped'
saveSerializedObjects(patient, savingPath)

savingPath = '/home/damien/Desktop/Patient0/Patient0_Model_bodyCropped'
dynMod.patient = None
saveSerializedObjects(dynMod, savingPath)
