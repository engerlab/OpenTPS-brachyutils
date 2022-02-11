from Core.Processing.DRRToolBox import computeDRRSet, computeDRRSequence, forwardProjection
from Core.IO.dataLoader import loadAllData
from Core.Data.dynamic3DSequence import Dynamic3DSequence
from Core.IO.serializedObjectIO import saveSerializedObject
from Core.Data.dynamic3DModel import Dynamic3DModel
from pydicom.uid import generate_uid
import matplotlib.pyplot as plt

## read a 4DCT
dataPath = "/media/damien/data/ImageData/Liver/Patient0/4DCT/"
dataList = loadAllData(dataPath)
print(len(dataList))
print(type(dataList[0]))

## create a Dynamic3DSequence
dynseq = Dynamic3DSequence(dyn3DImageList=dataList)

## use the forward projection directly on a numpy array with an angle of 0
img = dynseq.dyn3DImageList[0].imageArray
DRR = forwardProjection(img, 90, axis='X')

plt.figure()
plt.imshow(DRR)
plt.show()

print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

# use it on a CTImage with 3 angles, then get back a list of DRR that can be added to a patient
anglesAndAxisList = [[0, 'Z'],
                    [30, 'X'],
                    [-10, 'Y']]

DRRSet = computeDRRSet(dynseq.dyn3DImageList[0], anglesAndAxisList)

for DRRImage in DRRSet:
    print(DRRImage.name)

plt.figure()
plt.subplot(1, 3, 1)
plt.imshow(DRRSet[0].imageArray)
plt.subplot(1, 3, 2)
plt.imshow(DRRSet[1].imageArray)
plt.subplot(1, 3, 3)
plt.imshow(DRRSet[2].imageArray)
plt.show()

print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

## use it on a CTImage with 2 angles, then get back a list of DRR that can be added to a patient
DRRSequence = computeDRRSequence(dynseq, anglesAndAxisList)

for DRRSet in DRRSequence:
    print('-----------')
    for DRRImage in DRRSet:
        print(DRRImage.name)

plt.figure()
plt.subplot(1, 3, 1)
plt.imshow(DRRSequence[0][1].imageArray)
plt.subplot(1, 3, 2)
plt.imshow(DRRSequence[5][1].imageArray)
plt.subplot(1, 3, 3)
plt.imshow(DRRSequence[2][0].imageArray)
plt.show()