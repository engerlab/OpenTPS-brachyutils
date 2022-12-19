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
from opentps.core.processing.imageProcessing.imageTransform3D import rotateData, translateData, applyTransform3D

logger = logging.getLogger(__name__)

def run():

    # GENERATE SYNTHETIC INPUT IMAGES
    fixed = CTImage()
    fixed.imageArray = np.full((20, 20, 20), -1000)
    fixed.imageArray[11:16, 5:14, 11:14] = 100.0

    moving = copy.copy(fixed)
    movingTrans = copy.copy(fixed)
    movingRot = copy.copy(fixed)
    movingBoth = copy.copy(fixed)

    translation = np.array([-5, 0, -2])
    rotation = np.array([0, -20, 0])
    rotCenter='imgCenter'

    ## Create a transform 3D
    print('Create a transform 3D')
    transform3D = Transform3D()
    transform3D.initFromTranslationAndRotationVectors(transVec=translation, rotVec=rotation)
    transform3D.setCenter(rotCenter)
    print('Translation', transform3D.getTranslation())
    print('Rotation', transform3D.getRotationAngles(inDegrees=True))

    print('moving with transform3D')
    moving = transform3D.deformImage(moving, outputBox='same')

    print('moving translation')
    translateData(movingTrans, translationInMM=translation)
    print('moving rotation')
    rotateData(movingRot, rotAnglesInDeg=rotation, rotCenter=rotCenter)
    movingRot = resampleImage3DOnImage3D(movingRot, fixedImage=fixed, fillValue=-1000)
    print('moving both')
    translateData(movingBoth, translationInMM=translation, outputBox='same')
    rotateData(movingBoth, rotAnglesInDeg=rotation, rotCenter=rotCenter, outputBox='same')

    y_slice = 10

    fig, ax = plt.subplots(1, 6)
    ax[0].set_title('fixed')
    ax[0].imshow(fixed.imageArray[:, y_slice, :])
    ax[0].set_xlabel(f"{fixed.origin}\n{fixed.spacing}\n{fixed.gridSize}")

    ax[1].set_title('translateData')
    ax[1].imshow(movingTrans.imageArray[:, y_slice, :])
    ax[1].set_xlabel(f"{movingTrans.origin}\n{movingTrans.spacing}\n{movingTrans.gridSize}")

    ax[2].set_title('rotateData')
    ax[2].imshow(movingRot.imageArray[:, y_slice, :])
    ax[2].set_xlabel(f"{movingRot.origin}\n{movingRot.spacing}\n{movingRot.gridSize}")

    ax[3].set_title('both')
    ax[3].imshow(movingBoth.imageArray[:, y_slice, :])
    ax[3].set_xlabel(f"{movingBoth.origin}\n{movingBoth.spacing}\n{movingBoth.gridSize}")

    ax[4].set_title('transform3D')
    ax[4].imshow(moving.imageArray[:, y_slice, :])
    ax[4].set_xlabel(f"{moving.origin}\n{moving.spacing}\n{moving.gridSize}")

    ax[5].set_title('transform3D-both')
    ax[5].imshow(moving.imageArray[:, y_slice, :] - movingBoth.imageArray[:, y_slice, :])

    plt.show()

    ## ---------------------------------------------------------------------------------

    # GENERATE SYNTHETIC INPUT IMAGES
    fixed = CTImage()
    fixed.imageArray = np.full((20, 20, 20), -1000)
    y_slice = 10

    pointList = [[15, y_slice, 15], [15, y_slice, 10], [12, y_slice, 12]]
    for point in pointList:
        fixed.imageArray[point[0], point[1], point[2]] = 200

    fieldFixed = VectorField3D()
    fieldFixed.imageArray = np.zeros((20, 20, 20, 3))
    vectorList = [np.array([2, 3, 4]), np.array([0, 3, 4]), np.array([7, 3, 3])]
    for pointIdx in range(len(pointList)):
        fieldFixed.imageArray[pointList[pointIdx][0], pointList[pointIdx][1], pointList[pointIdx][2]] = vectorList[
            pointIdx]

    moving = copy.copy(fixed)
    fieldMoving = copy.copy(fieldFixed)

    translation = np.array([0, 0, 0])
    rotation = np.array([0, -20, 0])
    rotCenter = 'imgCenter'

    ## Create a transform 3D
    print('Create a transform 3D')
    transform3D = Transform3D()
    transform3D.initFromTranslationAndRotationVectors(transVec=translation, rotVec=rotation)
    transform3D.setCenter(rotCenter)
    print('Translation', transform3D.getTranslation())
    print('Rotation', transform3D.getRotationAngles(inDegrees=True))

    print('moving with transform3D')
    moving = transform3D.deformImage(moving, outputBox='same')
    fieldMoving = transform3D.deformImage(fieldMoving)
    # moving = resampleImage3DOnImage3D(moving, fixedImage=fixed, fillValue=-1000)
    print('fixed.origin', fixed.origin, 'moving.origin', moving.origin)
    # fieldMoving = resampleImage3DOnImage3D(fieldMoving, fixedImage=fixed, fillValue=0)
    # print('fieldFixed.origin', fieldFixed.origin, 'fieldMoving.origin', fieldMoving.origin)

    compXFixed = fieldFixed.imageArray[:, y_slice, :, 0]
    compZFixed = fieldFixed.imageArray[:, y_slice, :, 2]
    compXMoving = fieldMoving.imageArray[:, y_slice, :, 0]
    compZMoving = fieldMoving.imageArray[:, y_slice, :, 2]

    # Plot X-Z field
    fig, ax = plt.subplots(1, 2)
    ax[0].imshow(fixed.imageArray[:, y_slice, :])
    ax[0].quiver(compXFixed, compZFixed, alpha=0.5, color='red', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[1].imshow(moving.imageArray[:, y_slice, :])
    ax[1].quiver(compXMoving, compZMoving, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
    plt.show()


    ## Rigid registration part --------------------------------------------------------------------
    # GENERATE SYNTHETIC INPUT IMAGES
    # fixed = CTImage()
    # fixed.imageArray = np.full((20, 20, 20), -1000)
    # y_slice = 10
    # pointList = [[15, y_slice, 15], [15, y_slice, 10], [12, y_slice, 12]]
    # for point in pointList:
    #     fixed.imageArray[point[0], point[1], point[2]] = 1
    #
    # fieldFixed = VectorField3D()
    # fieldFixed.imageArray = np.zeros((20, 20, 20, 3))
    # vectorList = [np.array([2, 3, 4]), np.array([0, 3, 4]), np.array([7, 3, 3])]
    # for pointIdx in range(len(pointList)):
    #     fieldFixed.imageArray[pointList[pointIdx][0], pointList[pointIdx][1], pointList[pointIdx][2]] = vectorList[
    #         pointIdx]
    #
    # moving = copy.copy(fixed)
    # moving2 = copy.copy(fixed)
    # fieldMoving = copy.copy(fieldFixed)
    #
    # transform3D = Transform3D()
    # transform3D.initFromTranslationAndRotationVectors(transVec=translation, rotVec=rotation)
    # print('Translation', transform3D.getTranslation(), '\n')
    # print('Rotation in deg', transform3D.getRotationAngles(inDegrees=True))
    #
    # transform3D.deformImage(moving)
    #
    # reg = RegistrationRigid(fixed, moving)
    # transformReg = reg.compute()
    # print('Translation', transformReg.getTranslation(), '\n')
    # print('Rotation in deg', transformReg.getRotationAngles(inDegrees=True))



if __name__ == "__main__":
    run()