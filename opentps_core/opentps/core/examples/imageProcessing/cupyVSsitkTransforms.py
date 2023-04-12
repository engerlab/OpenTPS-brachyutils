import copy

import matplotlib.pyplot as plt
import logging

from opentps.core.data.images import VectorField3D
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel
from opentps.core.data._transform3D import Transform3D
from opentps.core.examples.showStuff import showModelWithAnimatedFields
from opentps.core.examples.syntheticData import *
from opentps.core.processing.imageProcessing.resampler3D import resampleImage3DOnImage3D
from opentps.core.processing.imageProcessing.imageTransform3D import rotateData, translateData
from opentps.core.processing.imageProcessing.resampler3D import resample

logger = logging.getLogger(__name__)

def run():

    imgSize = [19, 19, 19]

    # GENERATE SYNTHETIC INPUT IMAGES
    fixed = CTImage()
    fixed.spacing = np.array([1, 1, 1])
    fixed.imageArray = np.full(imgSize, -1000)
    fixed.imageArray[11:16, 6:14, 11:14] = 100.0

    y_slice = 10
    pointList = [[11, y_slice, 13], [15, y_slice, 11], [12, y_slice, 12], [11, y_slice, 11]]
    # pointList=[]

    fieldFixed = VectorField3D()
    fieldFixed.imageArray = np.zeros((imgSize[0], imgSize[1], imgSize[2], 3))
    vectorList = [np.array([2, 3, 4]), np.array([0, 3, 4]), np.array([7, 3, 3]), np.array([2, 0, 0])]
    for pointIdx in range(len(pointList)):
        fieldFixed.imageArray[pointList[pointIdx][0], pointList[pointIdx][1], pointList[pointIdx][2]] = vectorList[
            pointIdx]

    translation = np.array([-2, 0, -5])
    rotation = np.array([0, 20, 0])
    rotCenter = 'imgCenter'
    outputBox = 'same'

    ## Test using a Transform3D ---------------------------------------------------------------------
    print('-' * 40)

    movingCupy = copy.deepcopy(fixed)
    movingSitk = copy.deepcopy(fixed)
    fieldMovingCupy = copy.deepcopy(fieldFixed)
    fieldMovingSitk = copy.deepcopy(fieldFixed)

    ## Create a transform 3D
    print('Create a transform 3D')
    transform3D = Transform3D()
    transform3D.initFromTranslationAndRotationVectors(transVec=translation, rotVec=rotation)
    transform3D.setCenter(rotCenter)
    print('Translation', transform3D.getTranslation())
    print('Rotation', transform3D.getRotationAngles(inDegrees=True))

    print('Moving with transform3D')
    movingCupy = transform3D.deformData(movingCupy, outputBox=outputBox, fillValue=-1000, tryGPU=True)
    fieldMovingCupy = transform3D.deformData(fieldMovingCupy, outputBox=outputBox, fillValue=0, tryGPU=True)

    movingSitk = transform3D.deformData(movingSitk, outputBox=outputBox, fillValue=-1000)
    fieldMovingSitk = transform3D.deformData(fieldMovingSitk, outputBox=outputBox, fillValue=0)

    compXFixed = fieldFixed.imageArray[:, y_slice, :, 0]
    compZFixed = fieldFixed.imageArray[:, y_slice, :, 2]
    compXMovingCupy = fieldMovingCupy.imageArray[:, y_slice, :, 0]
    compZMovingCupy = fieldMovingCupy.imageArray[:, y_slice, :, 2]
    compXMovingSITK = fieldMovingSitk.imageArray[:, y_slice, :, 0]
    compZMovingSITK = fieldMovingSitk.imageArray[:, y_slice, :, 2]

    # Plot X-Z field
    fig, ax = plt.subplots(1, 4)
    fig.suptitle('Test using a Transform3D')

    ax[0].set_title('Fixed')
    ax[0].imshow(fixed.imageArray[:, y_slice, :])
    ax[0].quiver(compZFixed, compXFixed, alpha=0.5, color='red', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[0].set_xlabel(f"{fixed.origin}\n{fixed.spacing}\n{fixed.gridSize}")

    ax[1].set_title('Moving Cupy')
    ax[1].imshow(movingCupy.imageArray[:, y_slice, :])
    ax[1].quiver(compZMovingCupy, compXMovingCupy, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[1].set_xlabel(f"{movingCupy.origin}\n{movingCupy.spacing}\n{movingCupy.gridSize}")

    ax[2].set_title('Moving SITK')
    ax[2].imshow(movingSitk.imageArray[:, y_slice, :])
    ax[2].quiver(compZMovingSITK, compXMovingSITK, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[2].set_xlabel(f"{movingSitk.origin}\n{movingSitk.spacing}\n{movingSitk.gridSize}")

    ax[3].set_title('Img diff')
    ax[3].imshow(movingCupy.imageArray[:, y_slice, :]-movingSitk.imageArray[:, y_slice, :])

    plt.show()

    ## Test using translateData ---------------------------------------------------------------------
    print('-' * 40)

    movingCupy = copy.deepcopy(fixed)
    movingSitk = copy.deepcopy(fixed)
    fieldMovingCupy = copy.deepcopy(fieldFixed)
    fieldMovingSitk = copy.deepcopy(fieldFixed)

    print('Moving with translateData')
    translateData(movingCupy, translationInMM=translation, outputBox=outputBox, fillValue=-1000, tryGPU=True)
    translateData(fieldMovingCupy, translationInMM=translation, outputBox=outputBox, fillValue=0, tryGPU=True)

    translateData(movingSitk, translationInMM=translation, outputBox=outputBox, fillValue=-1000)
    translateData(fieldMovingSitk, translationInMM=translation, outputBox=outputBox, fillValue=0)

    compXFixed = fieldFixed.imageArray[:, y_slice, :, 0]
    compZFixed = fieldFixed.imageArray[:, y_slice, :, 2]
    compXMovingCupy = fieldMovingCupy.imageArray[:, y_slice, :, 0]
    compZMovingCupy = fieldMovingCupy.imageArray[:, y_slice, :, 2]
    compXMovingSITK = fieldMovingSitk.imageArray[:, y_slice, :, 0]
    compZMovingSITK = fieldMovingSitk.imageArray[:, y_slice, :, 2]

    # Plot X-Z field
    fig, ax = plt.subplots(1, 4)
    fig.suptitle('Test using translateData')

    ax[0].set_title('Fixed')
    ax[0].imshow(fixed.imageArray[:, y_slice, :])
    ax[0].quiver(compZFixed, compXFixed, alpha=0.5, color='red', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[0].set_xlabel(f"{fixed.origin}\n{fixed.spacing}\n{fixed.gridSize}")

    ax[1].set_title('Moving Cupy')
    ax[1].imshow(movingCupy.imageArray[:, y_slice, :])
    ax[1].quiver(compZMovingCupy, compXMovingCupy, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2,
                 width=.010)
    ax[1].set_xlabel(f"{movingCupy.origin}\n{movingCupy.spacing}\n{movingCupy.gridSize}")

    ax[2].set_title('Moving SITK')
    ax[2].imshow(movingSitk.imageArray[:, y_slice, :])
    ax[2].quiver(compZMovingSITK, compXMovingSITK, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2,
                 width=.010)
    ax[2].set_xlabel(f"{movingSitk.origin}\n{movingSitk.spacing}\n{movingSitk.gridSize}")

    ax[3].set_title('Img diff')
    ax[3].imshow(movingCupy.imageArray[:, y_slice, :] - movingSitk.imageArray[:, y_slice, :])

    plt.show()

    ## Test using rotateData ---------------------------------------------------------------------
    print('-' * 40)

    movingCupy = copy.deepcopy(fixed)
    movingSitk = copy.deepcopy(fixed)
    fieldMovingCupy = copy.deepcopy(fieldFixed)
    fieldMovingSitk = copy.deepcopy(fieldFixed)

    print('Moving with rotateData')
    rotateData(movingCupy, rotAnglesInDeg=rotation, outputBox=outputBox, fillValue=-1000, rotCenter=rotCenter, tryGPU=True)
    rotateData(fieldMovingCupy, rotAnglesInDeg=rotation, outputBox=outputBox, fillValue=0, rotCenter=rotCenter, tryGPU=True)

    rotateData(movingSitk, rotAnglesInDeg=rotation, outputBox=outputBox, fillValue=-1000, rotCenter=rotCenter)
    rotateData(fieldMovingSitk, rotAnglesInDeg=rotation, outputBox=outputBox, fillValue=0, rotCenter=rotCenter)

    compXFixed = fieldFixed.imageArray[:, y_slice, :, 0]
    compZFixed = fieldFixed.imageArray[:, y_slice, :, 2]
    compXMovingCupy = fieldMovingCupy.imageArray[:, y_slice, :, 0]
    compZMovingCupy = fieldMovingCupy.imageArray[:, y_slice, :, 2]
    compXMovingSITK = fieldMovingSitk.imageArray[:, y_slice, :, 0]
    compZMovingSITK = fieldMovingSitk.imageArray[:, y_slice, :, 2]

    # Plot X-Z field
    fig, ax = plt.subplots(1, 4)
    fig.suptitle('Test using rotateData')

    ax[0].set_title('Fixed')
    ax[0].imshow(fixed.imageArray[:, y_slice, :])
    ax[0].quiver(compZFixed, compXFixed, alpha=0.5, color='red', angles='xy', scale_units='xy', scale=2, width=.010)
    ax[0].set_xlabel(f"{fixed.origin}\n{fixed.spacing}\n{fixed.gridSize}")

    ax[1].set_title('Moving Cupy')
    ax[1].imshow(movingCupy.imageArray[:, y_slice, :])
    ax[1].quiver(compZMovingCupy, compXMovingCupy, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2,
                 width=.010)
    ax[1].set_xlabel(f"{movingCupy.origin}\n{movingCupy.spacing}\n{movingCupy.gridSize}")

    ax[2].set_title('Moving SITK')
    ax[2].imshow(movingSitk.imageArray[:, y_slice, :])
    ax[2].quiver(compZMovingSITK, compXMovingSITK, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2,
                 width=.010)
    ax[2].set_xlabel(f"{movingSitk.origin}\n{movingSitk.spacing}\n{movingSitk.gridSize}")

    ax[3].set_title('Img diff')
    ax[3].imshow(movingCupy.imageArray[:, y_slice, :] - movingSitk.imageArray[:, y_slice, :])

    plt.show()



if __name__ == "__main__":
    run()