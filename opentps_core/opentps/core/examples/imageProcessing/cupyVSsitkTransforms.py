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

    imgSize = [40, 40, 40]
    imgSpacing = [1, 1, 2]
    objectBorder = [[21, 33], [int(imgSize[1]/4), 3*int(imgSize[1]/4)], [21, 34]]

    translation = np.array([-10.22, 0, -14.56])
    rotation = np.array([0, 30, 0])
    rotCenter = 'imgCenter'
    outputBox = 'same'
    interpOrder = 1

    # GENERATE SYNTHETIC INPUT IMAGES
    fixed = CTImage()
    fixed.spacing = np.array(imgSpacing)
    fixed.imageArray = np.full(imgSize, -1000)
    fixed.imageArray[objectBorder[0][0]: objectBorder[0][1],
                    objectBorder[1][0]: objectBorder[1][1],
                    objectBorder[2][0]: objectBorder[2][1]] = 100.0

    y_slice = int(imgSize[1]/2)
    pointList = [[objectBorder[0][0], y_slice, objectBorder[2][1]-1],
                 [objectBorder[0][1]-1, y_slice, objectBorder[2][0]],
                 [objectBorder[0][0]+1, y_slice, objectBorder[2][0]+1],
                 [objectBorder[0][0], y_slice, objectBorder[2][0]]]

    fieldFixed = VectorField3D()
    fieldFixed.imageArray = np.zeros((imgSize[0], imgSize[1], imgSize[2], 3))
    fieldFixed.spacing = np.array(imgSpacing)
    vectorList = [np.array([4, 6, 8]), np.array([0, 6, 8]), np.array([14, 6, 6]), np.array([6, 0, 0])]
    for pointIdx in range(len(pointList)):
        fieldFixed.imageArray[pointList[pointIdx][0], pointList[pointIdx][1], pointList[pointIdx][2]] = vectorList[
            pointIdx]

    maskFixed = ROIMask()
    maskFixed.spacing = np.array(imgSpacing)
    maskFixed.imageArray = np.zeros(imgSize).astype(bool)
    maskFixed.imageArray[objectBorder[0][0]: objectBorder[0][1],
                        objectBorder[1][0]: objectBorder[1][1],
                        objectBorder[2][0]: objectBorder[2][1]] = True


    ## this function is just to see the results
    def showImagesAndFieldAndMask(fixed, movingCupy, movingSitk, fieldFixed, fieldMovingCupy, fieldMovingSitk,
                                  maskFixed, maskMovingCupy, maskMovingSitk, y_slice, figTitle, showImage=True,
                                  showField=True, showMask=True, ):

        compXFixed = fieldFixed.imageArray[:, y_slice, :, 0]
        compZFixed = fieldFixed.imageArray[:, y_slice, :, 2]
        compXMovingCupy = fieldMovingCupy.imageArray[:, y_slice, :, 0]
        compZMovingCupy = fieldMovingCupy.imageArray[:, y_slice, :, 2]
        compXMovingSITK = fieldMovingSitk.imageArray[:, y_slice, :, 0]
        compZMovingSITK = fieldMovingSitk.imageArray[:, y_slice, :, 2]

        fig, ax = plt.subplots(2, 3)
        fig.suptitle(figTitle)

        if showImage:
            ax[0, 0].imshow(fixed.imageArray[:, y_slice, :])
            ax[0, 1].imshow(movingCupy.imageArray[:, y_slice, :])
            ax[0, 2].imshow(movingSitk.imageArray[:, y_slice, :])
            ax[1, 0].imshow(movingCupy.imageArray[:, y_slice, :] - movingSitk.imageArray[:, y_slice, :])
            ax[1, 0].set_xlabel('Img diff')
        if showField:
            ax[0, 0].quiver(compZFixed, compXFixed, alpha=0.5, color='red', angles='xy', scale_units='xy', scale=2, width=.010)
            ax[0, 1].quiver(compZMovingCupy, compXMovingCupy, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
            ax[0, 2].quiver(compZMovingSITK, compXMovingSITK, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
            ax[1, 1].quiver(compZMovingCupy - compZMovingSITK, compXMovingCupy - compXMovingSITK, alpha=0.5, color='green', angles='xy', scale_units='xy', scale=2, width=.010)
            ax[1, 1].set_xlabel('Field diff')
        if showMask:
            ax[0, 0].imshow(maskFixed.getBinaryContourMask(internalBorder=True).imageArray[:, y_slice, :], alpha=0.5, cmap='Reds')
            ax[0, 1].imshow(maskMovingCupy.getBinaryContourMask(internalBorder=True).imageArray[:, y_slice, :], alpha=0.5, cmap='Reds')
            ax[0, 2].imshow(maskMovingSitk.getBinaryContourMask(internalBorder=True).imageArray[:, y_slice, :], alpha=0.5, cmap='Reds')
            ax[1, 2].imshow(maskMovingCupy.getBinaryContourMask(internalBorder=True).imageArray[:, y_slice, :] ^ maskMovingSitk.getBinaryContourMask(internalBorder=True).imageArray[:, y_slice, :], alpha=0.5, cmap='Reds')
            ax[1, 2].set_xlabel('Mask diff')

        ax[0, 0].set_title('Fixed')
        ax[0, 0].set_xlabel(f"{fixed.origin}\n{fixed.spacing}\n{fixed.gridSize}")
        ax[0, 1].set_title('Moving Cupy')
        ax[0, 1].set_xlabel(f"{movingCupy.origin}\n{movingCupy.spacing}\n{movingCupy.gridSize}")
        ax[0, 2].set_title('Moving SITK')
        ax[0, 2].set_xlabel(f"{movingSitk.origin}\n{movingSitk.spacing}\n{movingSitk.gridSize}")

        plt.show()
    ## -----------------------------------------------------------------------------------------------


    ## Test using a Transform3D ---------------------------------------------------------------------
    print('-' * 40)

    movingCupy = copy.deepcopy(fixed)
    movingSitk = copy.deepcopy(fixed)
    fieldMovingCupy = copy.deepcopy(fieldFixed)
    fieldMovingSitk = copy.deepcopy(fieldFixed)
    maskMovingCupy = copy.deepcopy(maskFixed)
    maskMovingSitk = copy.deepcopy(maskFixed)

    ## Create a transform 3D
    print('Create a transform 3D')
    transform3D = Transform3D()
    transform3D.initFromTranslationAndRotationVectors(transVec=translation, rotVec=rotation)
    transform3D.setCenter(rotCenter)
    print('Translation', transform3D.getTranslation())
    print('Rotation', transform3D.getRotationAngles(inDegrees=True))

    print('Moving with transform3D')
    movingCupy = transform3D.deformData(movingCupy, outputBox=outputBox, fillValue=-1000, tryGPU=True)
    fieldMovingCupy = transform3D.deformData(fieldMovingCupy, outputBox=outputBox, tryGPU=True)
    maskMovingCupy = transform3D.deformData(maskMovingCupy, outputBox=outputBox, tryGPU=True)

    movingSitk = transform3D.deformData(movingSitk, outputBox=outputBox, fillValue=-1000)
    fieldMovingSitk = transform3D.deformData(fieldMovingSitk, outputBox=outputBox)
    maskMovingSitk = transform3D.deformData(maskMovingSitk, outputBox=outputBox)

    showImagesAndFieldAndMask(fixed, movingCupy, movingSitk, fieldFixed, fieldMovingCupy, fieldMovingSitk,
                                  maskFixed, maskMovingCupy, maskMovingSitk, y_slice, figTitle='Test using a Transform3D')


    ## Test using translateData ---------------------------------------------------------------------
    print('-' * 40)

    movingCupy = copy.deepcopy(fixed)
    movingSitk = copy.deepcopy(fixed)
    fieldMovingCupy = copy.deepcopy(fieldFixed)
    fieldMovingSitk = copy.deepcopy(fieldFixed)
    maskMovingCupy = copy.deepcopy(maskFixed)
    maskMovingSitk = copy.deepcopy(maskFixed)

    print('Moving with translateData')
    translateData(movingCupy, translationInMM=translation, outputBox=outputBox, fillValue=-1000, tryGPU=True, interpOrder=interpOrder)
    translateData(fieldMovingCupy, translationInMM=translation, outputBox=outputBox, tryGPU=True, interpOrder=interpOrder)
    translateData(maskMovingCupy, translationInMM=translation, outputBox=outputBox, tryGPU=True, interpOrder=interpOrder)

    translateData(movingSitk, translationInMM=translation, outputBox=outputBox, fillValue=-1000)
    translateData(fieldMovingSitk, translationInMM=translation, outputBox=outputBox)
    translateData(maskMovingSitk, translationInMM=translation, outputBox=outputBox)

    showImagesAndFieldAndMask(fixed, movingCupy, movingSitk, fieldFixed, fieldMovingCupy, fieldMovingSitk,
                              maskFixed, maskMovingCupy, maskMovingSitk, y_slice, figTitle='Test using translateData')

    ## Test using rotateData ---------------------------------------------------------------------
    print('-' * 40)

    movingCupy = copy.deepcopy(fixed)
    movingSitk = copy.deepcopy(fixed)
    fieldMovingCupy = copy.deepcopy(fieldFixed)
    fieldMovingSitk = copy.deepcopy(fieldFixed)
    maskMovingCupy = copy.deepcopy(maskFixed)
    maskMovingSitk = copy.deepcopy(maskFixed)

    print('Moving with rotateData')
    rotateData(movingCupy, rotAnglesInDeg=rotation, outputBox=outputBox, fillValue=-1000, rotCenter=rotCenter, tryGPU=True, interpOrder=interpOrder)
    rotateData(fieldMovingCupy, rotAnglesInDeg=rotation, outputBox=outputBox, rotCenter=rotCenter, tryGPU=True, interpOrder=interpOrder)
    rotateData(maskMovingCupy, rotAnglesInDeg=rotation, outputBox=outputBox, rotCenter=rotCenter, tryGPU=True, interpOrder=interpOrder)

    rotateData(movingSitk, rotAnglesInDeg=rotation, outputBox=outputBox, fillValue=-1000, rotCenter=rotCenter)
    rotateData(fieldMovingSitk, rotAnglesInDeg=rotation, outputBox=outputBox, rotCenter=rotCenter)
    rotateData(maskMovingSitk, rotAnglesInDeg=rotation, outputBox=outputBox, rotCenter=rotCenter)

    showImagesAndFieldAndMask(fixed, movingCupy, movingSitk, fieldFixed, fieldMovingCupy, fieldMovingSitk,
                              maskFixed, maskMovingCupy, maskMovingSitk, y_slice, figTitle='Test using rotateData')

if __name__ == "__main__":
    run()


