import math as m
import matplotlib.pyplot as plt
import numpy as np
import copy

from opentps.core.processing.imageProcessing.resampler3D import resample, resampleOnImage3D, resampleImage3DOnImage3D
from opentps.core.processing.registration.registrationRigid import RegistrationRigid
from opentps.core.processing.dataComparison.image3DComparison import getTranslationAndRotation
from opentps.core.processing.dataComparison.contourComparison import getBaselineShift, compareMasks
from opentps.core.data._transform3D import Transform3D
from opentps.core.processing.dataComparison.testShrink import eval
from opentps.core.processing.deformableDataAugmentationToolBox.modelManipFunctions import *
from opentps.core.processing.imageProcessing.syntheticDeformation import applyBaselineShift

def compareModels(dynMod1, dynMod2, structList1=[], structList2=[], fixedModel=1):
    """
    Compare two dynamic 3D models by registering them and comparing the masks

    Parameters
    ----------
    dynMod1 : Dynamic3DModel
        First dynamic 3D model to compare
    dynMod2 : Dynamic3DModel
        Second dynamic 3D model to compare
    structList1 : list of str
        List of the names of the structures to compare from the first model
    structList2 : list of str
        List of the names of the structures to compare from the second model
    fixedModel : int
        1 if the first model is the fixed model, 2 if the second model is the fixed model

    Returns
    -------
    results : list
        List of the baseline shifts between the masks of the two models. The first element is the Transform3D object
        from the rigid registration between the two models.
    """

    results = []

    if fixedModel == 1:
        fixedModel = dynMod1
        movingModel = dynMod2
        fixedMaskNameList = structList1
        movingMaskNameList = structList2
    else:
        fixedModel = dynMod2
        movingModel = dynMod1
        fixedMaskNameList = structList2
        movingMaskNameList = structList1

    print('Start comparison between the two models with fixed model:', fixedModel.name, 'and moving model:', movingModel.name)
    print('Rigid Registration between the two model midp images...')
    reg = RegistrationRigid(fixed=fixedModel.midp, moving=movingModel.midp)
    transform = reg.compute()
    results.append(transform)
    translation = transform.getTranslation()
    rotationInDeg = transform.getRotationAngles(inDegrees=True)
    print('Rigid Registration Done')
    print('Transform3D translation:', translation)
    print('Transform3D rotation in degrees:', rotationInDeg)

    # movingModel = resample(movingModel, spacing=fixedModel.midp.spacing, origin=fixedModel.midp.origin, gridSize=fixedModel.midp.gridSize, fillValue=-1000)
    # movingMidPCopy = copy.copy(movingModel.midp)
    # movingMidPDeformed = transform.deformData(movingMidPCopy, outputBox='same')

    # ySlice = 250
    #
    # fig, ax = plt.subplots(2, 3, figsize=(15, 8))
    # fig.suptitle(f'Rigid registration results: translation={translation} / rotation in degrees={rotationInDeg}')
    # ax[0, 0].imshow(np.rot90(fixedModel.midp.imageArray[:, ySlice, :]))
    # ax[0, 0].set_title('Fixed')
    # ax[0, 0].set_xlabel(f"{fixedModel.midp.origin}\n{fixedModel.midp.spacing}\n{fixedModel.midp.gridSize}")
    # ax[0, 1].imshow(np.rot90(movingModel.midp.imageArray[:, ySlice, :]))
    # ax[0, 1].set_title('Moving')
    # ax[0, 1].set_xlabel(f"{movingModel.midp.origin}\n{movingModel.midp.spacing}\n{movingModel.midp.gridSize}")
    # ax[0, 2].imshow(np.rot90(movingMidPDeformed.imageArray[:, ySlice, :]))
    # ax[0, 2].set_title('Moving deformed using the Transform3D from the rigid reg')
    # ax[0, 2].set_xlabel(f"{movingMidPDeformed.origin}\n{movingMidPDeformed.spacing}\n{movingMidPDeformed.gridSize}")
    # ax[1, 0].imshow(np.rot90(fixedModel.midp.imageArray[:, ySlice, :] - movingModel.midp.imageArray[:, ySlice, :]))
    # ax[1, 0].set_title('MidP diff before')
    # ax[1, 1].imshow(np.rot90(fixedModel.midp.imageArray[:, ySlice, :] - movingMidPDeformed.imageArray[:, ySlice, :]))
    # ax[1, 1].set_title('MidP diff after')
    # plt.show()

    if len(fixedMaskNameList) != len(movingMaskNameList):
        print('The two struct lists have not the same lenght, abort the mask comparison')
    else:
        for maskIdx in range(len(fixedMaskNameList)):
            fixedMask = fixedModel.getMaskByName(fixedMaskNameList[maskIdx])
            movingMask = movingModel.getMaskByName(movingMaskNameList[maskIdx])
            masksProps = compareMasks(fixedMask, movingMask)
            deformedMovingMask = transform.deformImage(movingMask)
            baselineShift = getBaselineShift(movingMask, fixedMask, transform=transform)
            results.append(baselineShift)
            print("baseline shift", baselineShift)


    return results

