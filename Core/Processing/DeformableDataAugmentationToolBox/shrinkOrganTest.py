import numpy as np
import matplotlib.pyplot as plt
from Core.Processing.DeformableDataAugmentationToolBox.modelManipFunctions import getVoxelIndexFromPosition


def shrinkOrgan(image, organContour, shrinkSize = 2):

    print('in shrink organ')

    # print(image2)


    gtvCenterOfMass = organContour.getCenterOfMass(image.origin, image.gridSize, image.spacing)
    gtvCenterOfMassInVoxels = getVoxelIndexFromPosition(gtvCenterOfMass, image)
    print('Used ROI name', organContour.name)
    print('Used ROI center of mass :', gtvCenterOfMass)
    print('Used ROI center of mass in voxels:', gtvCenterOfMassInVoxels)

    GTVMask = organContour.getBinaryMask(origin=image.origin, gridSize=image.gridSize,
                                       spacing=image.spacing)

    plt.figure()
    plt.imshow(image.imageArray[:, :, gtvCenterOfMassInVoxels[2]])
    plt.imshow(GTVMask.imageArray[:, :, gtvCenterOfMassInVoxels[2]], alpha=0.5)
    plt.show()

    

    return 0