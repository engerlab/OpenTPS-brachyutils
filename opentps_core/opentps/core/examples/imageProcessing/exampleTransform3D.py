import copy

import numpy as np
import matplotlib.pyplot as plt
import time
import logging

from opentps.core.data.images import CTImage
from opentps.core.data.images import VectorField3D
from opentps.core.data._transform3D import Transform3D
from opentps.core.processing.registration.registrationRigid import RegistrationRigid
from opentps.core.examples.syntheticData import *
from opentps.core.processing.imageProcessing.resampler3D import resampleImage3DOnImage3D
from opentps.core.processing.imageProcessing.sitkImageProcessing import rotateImage3DSitk, translateImage3DSitk

logger = logging.getLogger(__name__)

def run():

    # GENERATE SYNTHETIC INPUT IMAGES
    fixed = CTImage()
    fixed.imageArray = np.full((20, 20, 20), -1000)
    y_slice = 10
    pointList = [[15, y_slice, 15], [15, y_slice, 10], [12, y_slice, 12]]
    for point in pointList:
        fixed.imageArray[point[0], point[1], point[2]] = 1

    fieldFixed = VectorField3D()
    fieldFixed.imageArray = np.zeros((20, 20, 20, 3))
    vectorList = [np.array([2, 3, 4]), np.array([0, 3, 4]), np.array([7, 3, 3])]
    for pointIdx in range(len(pointList)):
        fieldFixed.imageArray[pointList[pointIdx][0], pointList[pointIdx][1], pointList[pointIdx][2]] = vectorList[pointIdx]

    translation = np.array([-5, 0, -3])
    rotation = np.array([0, 0, 0])

    moving = copy.copy(fixed)
    fieldMoving = copy.copy(fieldFixed)


    ## Create a transform 3D
    print('Create a transform 3D')
    transform3D = Transform3D()
    transform3D.initFromTranslationAndRotationVectors(translation, rotation)
    print(transform3D.getTranslation())
    print(transform3D.getRotationAngles(inDegrees=True))
    print('---------------')
    moving = transform3D.deformImage(moving)
    moving = resampleImage3DOnImage3D(moving, fixedImage=fixed, fillValue=-1000)
    print(fixed.origin, moving.origin)
    # translateImage3DSitk(moving, translationInMM=translation)



    compXFixed = fieldFixed.imageArray[:, y_slice, :, 0]
    compZFixed = fieldFixed.imageArray[:, y_slice, :, 2]
    compXMoving = fieldMoving.imageArray[:, y_slice, :, 0]
    compZMoving = fieldMoving.imageArray[:, y_slice, :, 2]

    # Plot X-Z field
    fig, ax = plt.subplots(1, 2)
    ax[0].imshow(fixed.imageArray[:, y_slice, :])
    # ax[0].quiver(compXFixed, compZFixed, alpha=0.5, color='red', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[1].imshow(moving.imageArray[:, y_slice, :])
    # ax[1].quiver(compXMoving, compZMoving, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
    plt.show()

    # ## option 1
    # transform3D = Transform3D()
    # transform3D.initFromTranslationAndRotationVectors(translation, rotation)
    # print('option 1')
    # print(transform3D.tform)
    # print(transform3D.getTranslation())
    # print(transform3D.getRotationAngles(inDegrees=True))
    # print('---------------')
    # moving = transform3D.deformImage(moving)
    # # resampledOnFixedGrid = resampleImage3DOnImage3D(moving, fixedImage=fixed, fillValue=-1000)
    #
    # inverseTest = copy.copy(moving)
    # transform3D = Transform3D()
    # transform3D.initFromTranslationAndRotationVectors(-translation, -rotation)
    # print('option 1 inversed')
    # print(transform3D.tform)
    # print(transform3D.getTranslation())
    # print(transform3D.getRotationAngles(inDegrees=True))
    # print('---------------')
    # inverseTest = transform3D.deformImage(inverseTest)
    # inverseTest = resampleImage3DOnImage3D(inverseTest, fixedImage=fixed, fillValue=-1000)
    # y_slice = 95
    # plt.figure()
    # plt.imshow(fixed.imageArray[:, y_slice, :]-inverseTest.imageArray[:, y_slice, :])
    # plt.show()

    ## option 2
    translateImage3DSitk(moving, translation)
    rotateImage3DSitk(moving, rotation, center='imgCenter')
    # print('option 2')
    # print('---------------')

    inverseTest = copy.copy(moving)
    rotateImage3DSitk(inverseTest, -rotation)
    translateImage3DSitk(inverseTest, -translation)
    # y_slice = 95
    plt.figure()
    plt.imshow(fixed.imageArray[:, y_slice, :]-inverseTest.imageArray[:, y_slice, :])
    plt.show()

    transform3D = Transform3D()
    transform3D.initFromTranslationAndRotationVectors(-translation, -rotation)
    print(transform3D.tform)
    print(transform3D.getTranslation())
    print(transform3D.getRotationAngles(inDegrees=True))

    # # PERFORM REGISTRATION
    # start_time = time.time()
    # reg = RegistrationRigid(fixed, moving)
    # transform = reg.compute()
    #
    # processing_time = time.time() - start_time
    # print('Registration processing time was', processing_time, '\n')
    # print('Rotation in rad', transform.getRotationAngles())
    # print('Rotation in deg', transform.getRotationAngles(inDegrees=True))
    # print('Translation', transform.getTranslation())


    # deformedImage = transform3D.deformImage(moving)
    # resampledOnFixedGrid = resampleImage3DOnImage3D(deformedImage, fixedImage=fixed, fillValue=-1000)

    # y_slice = 95
    # fig, ax = plt.subplots(2, 3)
    # ax[0, 0].imshow(fixed.imageArray[:, y_slice, :])
    # ax[0, 0].set_title('Fixed')
    # ax[0, 0].set_xlabel('Origin: '+f'{fixed.origin[0]}'+','+f'{fixed.origin[1]}'+','+f'{fixed.origin[2]}')
    # ax[0, 1].imshow(moving.imageArray[:, y_slice, :])
    # ax[0, 1].set_title('Moving')
    # ax[0, 1].set_xlabel('Origin: ' + f'{moving.origin[0]}' + ',' + f'{moving.origin[1]}' + ',' + f'{moving.origin[2]}')
    # ax[0, 2].imshow(fixed.imageArray[:, y_slice, :]-moving.imageArray[:, y_slice, :])
    # ax[0, 2].set_title('Diff')
    # ax[1, 0].imshow(deformedImage.imageArray[:, y_slice, :])
    # ax[1, 0].set_title('DeformedMoving')
    # ax[1, 0].set_xlabel('Origin: ' + f'{deformedImage.origin[0]:.1f}' + ',' + f'{deformedImage.origin[1]:.1f}' + ',' + f'{deformedImage.origin[2]:.1f}')
    # ax[1, 1].imshow(resampledOnFixedGrid.imageArray[:, y_slice, :])
    # ax[1, 1].set_title('resampledOnFixedGrid')
    # ax[1, 1].set_xlabel('Origin: ' + f'{resampledOnFixedGrid.origin[0]:.1f}' + ',' + f'{resampledOnFixedGrid.origin[1]:.1f}' + ',' + f'{resampledOnFixedGrid.origin[2]:.1f}')
    # ax[1, 2].imshow(fixed.imageArray[:, y_slice, :] - resampledOnFixedGrid.imageArray[:, y_slice, :])
    # ax[1, 2].set_title('Diff')
    # plt.show()

if __name__ == "__main__":
    run()