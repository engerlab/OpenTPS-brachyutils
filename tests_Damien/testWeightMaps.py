from Core.IO.dicomReader import readDicomCT
from Core.IO.dataLoader import listAllFiles
from Core.Processing.DeformableDataAugmentationToolBox.weightMaps import getWeightMapsAsImage3DList
import numpy as np
import matplotlib.pyplot as plt
import math


dataPath = "/media/damien/data/ImageData/Liver/Patient0/4DCT/p30"
filesList = listAllFiles(dataPath)
print(filesList)
image1 = readDicomCT(filesList['Dicom'])
print(type(image1))
print(image1.gridSize)
print(image1.origin)
print(image1.spacing)

numberOfMeasurePoints = 3
internalPoints = []

for pointIndex in range(numberOfMeasurePoints):
    # randomTriplet = [np.random.rand(1) * (image1.gridSize[0] * image1.spacing[0]) + image1.origin[0],
    #                  np.random.rand(1) * (image1.gridSize[1] * image1.spacing[1]) + image1.origin[1],
    #                  np.random.rand(1) * (image1.gridSize[2] * image1.spacing[2]) + image1.origin[2]]
    randomTriplet = [np.random.rand(1) * (image1.gridSize[0] * image1.spacing[0]) + image1.origin[0],
                     np.random.rand(1) * (image1.gridSize[1] * image1.spacing[1]) + image1.origin[1],
                     (image1.gridSize[2] * image1.spacing[2])/2 + image1.origin[2]]
    internalPoints.append(randomTriplet)

print(internalPoints)

internalPoints[0] = [0, -200, (image1.gridSize[2] * image1.spacing[2])/2 + image1.origin[2]]
internalPoints[1] = [0, -100, (image1.gridSize[2] * image1.spacing[2])/2 + image1.origin[2]]
internalPoints[2] = [0, 100, (image1.gridSize[2] * image1.spacing[2])/2 + image1.origin[2]]
#internalPoints[3] = [0, 200, (image1.gridSize[2] * image1.spacing[2])/2 + image1.origin[2]]

weightMapList = getWeightMapsAsImage3DList(internalPoints, image1)

for weightMap in weightMapList:
    print(type(weightMap), weightMap.name)

numberOfRandomSlicesToShow = 5 ## use an odd number
halfSizeZ = int(image1.gridSize[2]/2)
sliceIndexes = [halfSizeZ-10, halfSizeZ-5, halfSizeZ, halfSizeZ+5, halfSizeZ+10]



fig, axes = plt.subplots(nrows=numberOfMeasurePoints, ncols=numberOfRandomSlicesToShow)
for i in range(len(axes)):
    for j in range(len(axes[0])):
        im = axes[i, j].imshow(weightMapList[i].imageArray[:, :, sliceIndexes[j]], vmin=0, vmax=1)
        if j == math.floor(numberOfRandomSlicesToShow/2):
            axes[i, j].plot([x[1] for x in internalPoints], [y[0] for y in internalPoints], "ok", label="input point")
        axes[i, j].axis('off')

fig.subplots_adjust(right=0.8)
cbar_ax = fig.add_axes([0.85, 0.15, 0.05, 0.7])
fig.colorbar(im, cax=cbar_ax)

plt.show()


totalWeightMap = np.zeros(weightMapList[0].gridSize)
for weightMap in weightMapList:
    totalWeightMap += weightMap.imageArray

print(np.min(totalWeightMap), np.max(totalWeightMap))

plt.figure()
plt.imshow(totalWeightMap[:, :, 3])
plt.show()