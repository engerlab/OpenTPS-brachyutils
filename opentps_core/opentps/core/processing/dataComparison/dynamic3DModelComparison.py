import math as m 
import numpy as np

from opentps.core.processing.imageProcessing.resampler3D import resample, resampleOnImage3D, resampleImage3DOnImage3D
from opentps.core.processing.registration.registrationRigid import RegistrationRigid
from opentps.core.processing.dataComparison.image3DComparison import getTranslationAndRotation
from opentps.core.processing.dataComparison.contourComparison import getBaselineShift
from opentps.core.processing.dataComparison.testShrink import eval

def compareModels(model1, model2, targetContourToUse1, targetContourToUse2):
    dynMod1 = model1.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct1 = model1.getPatientDataOfType("RTStruct")[0]

    print('Available ROIs for model 1')
    rtStruct1.print_ROINames()

    dynMod2 = model2.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct2 = model2.getPatientDataOfType("RTStruct")[0]

    print('Available ROIs for model 2')
    rtStruct2.print_ROINames()
    
    dynMod1 = resample(dynMod1, spacing=[1, 1, 1], gridSize=dynMod1.midp.gridSize, origin=dynMod1.midp.origin)
    dynMod2 = resample(dynMod2, spacing=[1, 1, 1], gridSize=dynMod1.midp.gridSize, origin=dynMod1.midp.origin)

    midP1 = dynMod1.midp
    midP2 = dynMod2.midp

    #midP2 = resampleImage3DOnImage3D(midP2, fixedImage=midP1, fillValue=-1000)

    reg = RegistrationRigid(fixed=midP1, moving=midP2)
    transform = reg.compute()

    translation, angles = getTranslationAndRotation(fixed=midP1, moving=midP2, transform=transform)
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
    deformedMask2 = transform.deformImage(GTVMask2)
    print(GTVMask1.imageArray.shape, deformedMask2.imageArray.shape)
    cm1 = GTVMask1.centerOfMass
    cm2 = deformedMask2.centerOfMass
    print("baseline shift", cm2 - cm1)
    deformedMask2 = resampleOnImage3D(data=deformedMask2, fixedImage=GTVMask1)
    #GTVMask2 = resampleImage3D(GTVMask2, spacing=[1, 1, 1])
    print(GTVMask1.imageArray.shape, deformedMask2.imageArray.shape)
    diff = deformedMask2.imageArray ^ GTVMask1.imageArray
    ligne = eval(deformedMask2.imageArray, diff)

    print("before transpose", deformedMask2.imageArray.shape, diff.shape)
    GTVMask2_t = deformedMask2.imageArray.transpose(0, 2, 1)
    diff_t = diff.transpose(0, 2, 1)
    print("after transpose 1", GTVMask2_t.shape, diff_t.shape)
    col = eval(GTVMask2_t, diff_t)

    GTVMask2_tt = GTVMask2_t.transpose(1,0,2)
    diff_tt = diff_t.transpose(1,0,2)
    print("after transpose 2", GTVMask2_tt.shape, diff_tt.shape)
    col2 = eval(GTVMask2_tt, diff_tt)

    print(np.mean(ligne), np.mean(col), np.mean(col2))
    print("in mm", np.mean(ligne)*GTVMask2.spacing[0], np.mean(col)*GTVMask2.spacing[1], np.mean(col2)*GTVMask2.spacing[2])
    baselineShift = getBaselineShift(fixedMask=GTVMask1, movingMask=GTVMask2, transform=transform)
    print("Baseline shift: ", baselineShift)
    print(len(ligne))
    print(ligne)
