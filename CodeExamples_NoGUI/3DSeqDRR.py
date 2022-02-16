from Core.Processing.DRRToolBox import computeDRRSet, computeDRRSequence, forwardProjection, createDRRDynamic2DSequence
from Core.IO.dataLoader import loadAllData
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.IO.serializedObjectIO import saveSerializedObject, loadDataStructure
from Core.Data.dynamic3DModel import Dynamic3DModel
from pydicom.uid import generate_uid
import matplotlib.pyplot as plt
# Import the os module
import os
from pathlib import Path

# Get the current working directory, its parent, then add the testData folder at the end of it
testDataPath = os.path.join(Path(os.getcwd()).parent.absolute(), 'testData/')

## read a serialized dynamic sequence
dataPath = testDataPath + "lightTest4DCT.p"
dynSeq = loadDataStructure(dataPath)[0]
print(type(dynSeq))
print(len(dynSeq.dyn3DImageList))
print(type(dynSeq.dyn3DImageList[0]))

## use the forward projection directly on a numpy array with an angle of 0
# img = dynSeq.dyn3DImageList[0].imageArray
# DRR = forwardProjection(img, 90, axis='X')

# plt.figure()
# plt.imshow(DRR)
# plt.show()

print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

# use it on a CTImage with 3 angles, then get back a list of DRR that can be added to a patient
anglesAndAxisList = [[0, 'Z'],
                    [30, 'X'],
                    [-10, 'Y']]

# DRRSet = computeDRRSet(dynSeq.dyn3DImageList[0], anglesAndAxisList)
#
# for DRRImage in DRRSet:
#     print(DRRImage.name)
#
# plt.figure()
# plt.subplot(1, 3, 1)
# plt.imshow(DRRSet[0].imageArray)
# plt.subplot(1, 3, 2)
# plt.imshow(DRRSet[1].imageArray)
# plt.subplot(1, 3, 3)
# plt.imshow(DRRSet[2].imageArray)
# plt.show()

print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

## use it on a CTImage with 2 angles, then get back a list of DRR that can be added to a patient
# DRRSequence = computeDRRSequence(dynSeq, anglesAndAxisList)
#
# for DRRSet in DRRSequence:
#     print('-----------')
#     for DRRImage in DRRSet:
#         print(DRRImage.name)
#
# plt.figure()
# plt.subplot(1, 3, 1)
# plt.imshow(DRRSequence[0][1].imageArray)
# plt.subplot(1, 3, 2)
# plt.imshow(DRRSequence[5][1].imageArray)
# plt.subplot(1, 3, 3)
# plt.imshow(DRRSequence[2][0].imageArray)
# plt.show()

testSetSeq = createDRRDynamic2DSequence(dynSeq, anglesAndAxisList)