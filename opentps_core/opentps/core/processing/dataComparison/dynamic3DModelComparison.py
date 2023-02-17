import math as m

import matplotlib.pyplot as plt
import numpy as np

from opentps.core.processing.imageProcessing.resampler3D import resample, resampleOnImage3D, resampleImage3DOnImage3D
from opentps.core.processing.registration.registrationRigid import RegistrationRigid
from opentps.core.processing.dataComparison.image3DComparison import getTranslationAndRotation
from opentps.core.processing.dataComparison.contourComparison import getBaselineShift
from opentps.core.data._transform3D import Transform3D
from opentps.core.processing.dataComparison.testShrink import eval
from opentps.core.processing.deformableDataAugmentationToolBox.modelManipFunctions import *
from opentps.core.processing.imageProcessing.syntheticDeformation import applyBaselineShift
def compareModels(model1, model2, targetContourToUse1, targetContourToUse2):
    dynMod1 = model1.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct1 = model1.getPatientDataOfType("RTStruct")[0]

    print('Available ROIs for model 1')
    rtStruct1.print_ROINames()

    dynMod2 = model2.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct2 = model2.getPatientDataOfType("RTStruct")[0]

    print('Available ROIs for model 2')
    rtStruct2.print_ROINames()
    """
    plt.figure(figsize=(15,8))
    fig, ax = plt.subplots(1, 4, figsize=(15, 8))
    ax[0].imshow(dynMod1.midp.imageArray[:, 241, :].T)
    ax[0].set_title('MidP1 avant resampling')
    ax[1].imshow(dynMod2.midp.imageArray[:, 241, :].T)
    ax[1].set_title('MidP2 avant resampling')

    dynMod1 = resample(dynMod1, spacing=[1, 1, 1], origin=dynMod2.midp.origin, gridSize=dynMod2.midp.gridSize)
    dynMod2 = resample(dynMod2, spacing=[1, 1, 1], origin=dynMod2.midp.origin, gridSize=dynMod2.midp.gridSize)

    ax[2].imshow(dynMod1.midp.imageArray[:, 282, :].T)
    ax[2].set_title('MidP1 apres resampling')
    ax[3].imshow(dynMod2.midp.imageArray[:, 282, :].T)
    ax[3].set_title('MidP2 apres resampling')
    plt.show()
    """
    print("modele 1 avant resampling", dynMod1.midp.origin, dynMod1.midp.spacing, dynMod1.midp.gridSize)
    print("modele 2 avant resampling", dynMod2.midp.origin, dynMod2.midp.spacing, dynMod2.midp.gridSize)

    dynMod1 = resample(dynMod1, spacing=dynMod2.midp.spacing, origin=dynMod2.midp.origin, gridSize=dynMod2.midp.gridSize, fillValue=-1000)
    #dynMod2 = resample(dynMod2, spacing=[1,1,1], origin=dynMod2.midp.origin, gridSize=dynMod2.midp.gridSize, fillValue=-1000)
    midP1 = dynMod1.midp
    midP2 = dynMod2.midp
    #midP1 = resampleImage3DOnImage3D(image=midP1, fixedImage=midP2, fillValue=-1000)

    dynMod1.midp = midP1
    print("new midP", dynMod1.midp.origin, dynMod1.midp.spacing, dynMod1.midp.gridSize)
    print("modele 1 apres resampling", dynMod1.midp.origin, dynMod1.midp.spacing, dynMod1.midp.gridSize)
    print("modele 2 apres resampling", dynMod2.midp.origin, dynMod2.midp.spacing, dynMod2.midp.gridSize)

    reg = RegistrationRigid(fixed=midP2, moving=midP1)
    transform = reg.compute()

    translation, angles = getTranslationAndRotation(fixed=midP2, moving=midP1, transform=transform)
    theta_x = angles[0]
    theta_y = angles[1]
    theta_z = angles[2]

    print("Rx,Ry,Rz in degrees: ", (180 / m.pi) * theta_x,(180 / m.pi) * theta_y,(180 / m.pi) * theta_z)
    print("translation: ", translation)

    gtvContour1 = rtStruct1.getContourByName(targetContourToUse1)
    GTVMask1 = gtvContour1.getBinaryMask(origin=dynMod1.midp.origin, gridSize=dynMod1.midp.gridSize,
                                        spacing=dynMod1.midp.spacing)

    gtvContour2 = rtStruct2.getContourByName(targetContourToUse2)
    GTVMask2 = gtvContour2.getBinaryMask(origin=dynMod2.midp.origin, gridSize=dynMod2.midp.gridSize,
                                        spacing=dynMod2.midp.spacing)

    deformedModel1 = transform.deformImage(dynMod1)
    deformedMask1 = transform.deformImage(GTVMask1)
    baselineShift = getBaselineShift(movingMask=GTVMask1, fixedMask=GTVMask2, transform=transform)
    print("baseline shift", baselineShift)
    deformedModel1, deformedMask1 = applyBaselineShift(deformedModel1, deformedMask1, baselineShift, tryGPU=True)
    """
    print("test matrix sitk")
    rotationArray = np.array([(180 / m.pi) * theta_x, (180 / m.pi) * theta_y, (180 / m.pi) * theta_z])
    rotCenter = 'imgCenter'
    transform3D = Transform3D()
    transform3D.initFromTranslationAndRotationVectors(transVec=translation, rotVec=rotationArray)
    transform3D.setCenter(rotCenter)
    print(transform3D.tformMatrix)
    print(transform3D.rotCenter)
    """
