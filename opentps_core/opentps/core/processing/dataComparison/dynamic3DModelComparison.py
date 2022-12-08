import math as m 

from opentps.core.processing.imageProcessing.resampler3D import resample
from opentps.core.processing.dataComparison.image3DComparison import getTranslationAndRotation

def compareModels(model1, model2):
    dynMod1 = model1.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct1 = model1.getPatientDataOfType("RTStruct")[0]

    print('Available ROIs for model 1')
    rtStruct1.print_ROINames()

    dynMod2 = model2.getPatientDataOfType("Dynamic3DModel")[0]
    rtStruct2 = model2.getPatientDataOfType("RTStruct")[0]

    print('Available ROIs for model 2')
    rtStruct2.print_ROINames()
    
    dynMod1 = resample(dynMod1, spacing=[1, 1, 1])
    dynMod2 = resample(dynMod2, spacing=[1, 1, 1])
    
    midP1 = dynMod1.midp
    midP2 = dynMod2.midp
    
    translation, angles = getTranslationAndRotation(fixed=midP1, moving=midP2)
    theta_x = angles[0]
    theta_y = angles[1]
    theta_z = angles[2]
    print("Rx,Ry,Rz in degrees",(180 / m.pi) * theta_x,(180 / m.pi) * theta_y,(180 / m.pi) * theta_z)
    print("translation",translation)
