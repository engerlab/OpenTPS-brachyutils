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

    moving = copy.copy(fixed)
    moving2 = copy.copy(fixed)
    fieldMoving = copy.copy(fieldFixed)

    translation = np.array([0, 0, 0])
    rotation = np.array([0, 50, 0])

    ## Create a transform 3D
    print('Create a transform 3D')
    transform3D = Transform3D()
    transform3D.initFromTranslationAndRotationVectors(translation=translation, rotation=rotation)
    print('Translation', transform3D.getTranslation())
    print('Rotation', transform3D.getRotationAngles(inDegrees=True))

    print('moving 1')
    moving = transform3D.deformImage(moving)
    print('fixed.origin', fixed.origin, 'moving.origin', moving.origin)
    moving = resampleImage3DOnImage3D(moving, fixedImage=fixed, fillValue=-1000)
    print('fixed.origin', fixed.origin, 'moving.origin', moving.origin)

    print('moving 2')
    translateImage3DSitk(moving2, translationInMM=translation)
    rotateImage3DSitk(moving2, rotAngleInDeg=rotation)


    print('fixed.origin', fixed.origin, 'moving2.origin', moving2.origin)
    moving2 = resampleImage3DOnImage3D(moving2, fixedImage=fixed, fillValue=-1000)
    print('fixed.origin', fixed.origin, 'moving2.origin', moving2.origin)
    
    compXFixed = fieldFixed.imageArray[:, y_slice, :, 0]
    compZFixed = fieldFixed.imageArray[:, y_slice, :, 2]
    compXMoving = fieldMoving.imageArray[:, y_slice, :, 0]
    compZMoving = fieldMoving.imageArray[:, y_slice, :, 2]

    # Plot X-Z field
    fig, ax = plt.subplots(1, 4)
    ax[0].imshow(fixed.imageArray[:, y_slice, :])
    # ax[0].quiver(compXFixed, compZFixed, alpha=0.5, color='red', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[1].imshow(moving.imageArray[:, y_slice, :])
    # ax[1].quiver(compXMoving, compZMoving, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[2].imshow(moving2.imageArray[:, y_slice, :])
    # ax[1].quiver(compXMoving, compZMoving, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[3].imshow(moving.imageArray[:, y_slice, :] - moving2.imageArray[:, y_slice, :])
    # ax[1].quiver(compXMoving, compZMoving, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
    plt.show()


    ## Rigid registration part --------------------------------------------------------------------
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
        fieldFixed.imageArray[pointList[pointIdx][0], pointList[pointIdx][1], pointList[pointIdx][2]] = vectorList[
            pointIdx]

    moving = copy.copy(fixed)
    moving2 = copy.copy(fixed)
    fieldMoving = copy.copy(fieldFixed)

    transform3D = Transform3D()
    transform3D.initFromTranslationAndRotationVectors(translation=translation, rotation=rotation)
    print('Translation', transform3D.getTranslation(), '\n')
    print('Rotation in deg', transform3D.getRotationAngles(inDegrees=True))

    transform3D.deformImage(moving)

    reg = RegistrationRigid(fixed, moving)
    transformReg = reg.compute()
    print('Translation', transformReg.getTranslation(), '\n')
    print('Rotation in deg', transformReg.getRotationAngles(inDegrees=True))



if __name__ == "__main__":
    run()