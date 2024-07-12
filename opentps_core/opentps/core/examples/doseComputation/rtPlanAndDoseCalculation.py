import os
import logging
import sys

from matplotlib import pyplot as plt

from opentps.core.processing.imageProcessing.resampler3D import resampleImage3DOnImage3D
from opentps.core.processing.planOptimization.tools import evaluateClinical
sys.path.append('..')
import numpy as np

from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.io.scannerReader import readScanner
from opentps.core.io.serializedObjectIO import loadRTPlan, saveRTPlan
from opentps.core.io.dicomIO import readDicomDose, readDicomPlan
from opentps.core.io.dataLoader import readData
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareCTCalibration import MCsquareCTCalibration
from opentps.core.io import mcsquareIO
from opentps.core.data._dvh import DVH
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.io.mhdIO import exportImageMHD
from opentps.core.data.plan import PlanIonBeam
from opentps.core.data.plan import PlanIonLayer
from opentps.core.data.images import CTImage, DoseImage
from opentps.core.data import RTStruct
from opentps.core.data import Patient
from opentps.core.data.images import ROIMask
from pathlib import Path


logger = logging.getLogger(__name__)


def run(output_path=""):
    if(output_path != ""):
        output_path = output_path
    else:
        output_path = os.getcwd()
        
    logger.info('Files will be stored in {}'.format(output_path))

    # Create plan from scratch
    plan = RTPlan()
    plan.appendBeam(PlanIonBeam())
    plan.appendBeam(PlanIonBeam())
    plan.beams[1].gantryAngle = 120.
    plan.beams[0].appendLayer(PlanIonLayer(100))
    plan.beams[0].appendLayer(PlanIonLayer(90))
    plan.beams[1].appendLayer(PlanIonLayer(80))
    plan[0].layers[0].appendSpot([-1,0,1], [1,2,3], [0.1,0.2,0.3])
    plan[0].layers[1].appendSpot([0,1], [2,3], [0.2,0.3])
    plan[1].layers[0].appendSpot(1, 1, 0.5)
    # Save plan
    saveRTPlan(plan,os.path.join(output_path,'dummy_plan.tps'))

    # Load plan in OpenTPS format (serialized)
    plan2 = loadRTPlan(os.path.join(output_path,'dummy_plan.tps'))
    print(plan2[0].layers[1].spotWeights)
    print(plan[0].layers[1].spotWeights)

    # Load DICOM plan
    dicomPath = os.path.join(Path(os.getcwd()).parent.absolute(),'opentps','testData','Phantom')
    dataList = readData(dicomPath, maxDepth=1)
    plan3 = [d for d in dataList if isinstance(d, RTPlan)][0]
    # or provide path to RTPlan and read it
    # plan_path = os.path.join(Path(os.getcwd()).parent.absolute(),'opentps/testData/Phantom/Plan_SmallWaterPhantom_cropped_resampled_optimized.dcm')
    # plan3 = readDicomPlan(plan_path)

    ## Dose computation from plan
    # Choosing default Scanner and BDL
    doseCalculator = MCsquareDoseCalculator()
    doseCalculator.ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)
    doseCalculator.beamModel = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)
    doseCalculator.nbPrimaries = 1e7

    # Manually specify Scanner and BDL
    #openTPS_path = os.path.join(Path(os.getcwd()).parent.absolute(),'opentps','opentps_core','opentps')
    #MCSquarePath = os.path.join(openTPS_path, 'core', 'processing', 'doseCalculation', 'MCsquare')
    # doseCalculator = MCsquareDoseCalculator()
    #beamModel = mcsquareIO.readBDL(os.path.join(MCSquarePath, 'BDL', 'UMCG_P1_v2_RangeShifter.txt'))
    #doseCalculator.beamModel = beamModel
    # scannerPath = os.path.join(MCSquarePath, 'Scanners', 'UCL_Toshiba')
    # calibration = MCsquareCTCalibration(fromFiles=(os.path.join(scannerPath, 'HU_Density_Conversion.txt'),
    #                                                 os.path.join(scannerPath, 'HU_Material_Conversion.txt'),
    #                                                 os.path.join(MCSquarePath, 'Materials')))
    # doseCalculator.ctCalibration = calibration

    

    # Generic example: box of water with spherical target
    # Load CT & contours
    # ct = [d for d in dataList if isinstance(d, CTImage)][0]
    # struct = [d for d in dataList if isinstance(d, RTStruct)][0]
    # target = struct.getContourByName('TV')
    # body = struct.getContourByName('Body')                    
    
    # or create CT and contours
    ctSize = 20
    ct = CTImage()
    ct.name = 'CT'

    target = ROIMask()
    target.name = 'TV'
    target.spacing = ct.spacing
    target.color = (255, 0, 0)  # red
    targetArray = np.zeros((ctSize, ctSize, ctSize)).astype(bool)
    radius = 2.5
    x0, y0, z0 = (10, 10, 10)
    x, y, z = np.mgrid[0:ctSize:1, 0:ctSize:1, 0:ctSize:1]
    r = np.sqrt((x - x0) ** 2 + (y - y0) ** 2 + (z - z0) ** 2)
    targetArray[r < radius] = True
    target.imageArray = targetArray

    huAir = -1024.
    huWater = doseCalculator.ctCalibration.convertRSP2HU(1.)
    ctArray = huAir * np.ones((ctSize, ctSize, ctSize))
    ctArray[1:ctSize - 1, 1:ctSize - 1, 1:ctSize - 1] = huWater
    ctArray[targetArray>=0.5] = 50
    ct.imageArray = ctArray

    body = ROIMask()
    body.name = 'Body'
    body.spacing = ct.spacing
    body.color = (0, 0, 255)
    bodyArray = np.zeros((ctSize, ctSize, ctSize)).astype(bool)
    bodyArray[1:ctSize- 1, 1:ctSize - 1, 1:ctSize - 1] = True
    body.imageArray = bodyArray


    # If we want to crop the CT to the body contour (set everything else to -1024)
    #doseCalculator.overwriteOutsideROI = body

    # MCsquare simulation
    doseImage = doseCalculator.computeDose(ct, plan3)
    # or Load dicom dose
    #doseImage = [d for d in dataList if isinstance(d, DoseImage)][0]
    # or
    #dcm_dose_file = os.path.join(output_path, "Dose_SmallWaterPhantom_resampled_optimized.dcm")
    #doseImage = readDicomDose(dcm_dose_file)

    # Export dose
    #output_path = os.getcwd()
    #exportImageMHD(output_path, doseImage)

    # DVH
    dvh = DVH(target, doseImage)
    print("D95",dvh._D95)
    print("D5",dvh._D5)
    print("Dmax",dvh._Dmax)
    print("Dmin",dvh._Dmin)
    
    # Plot dose
    target = resampleImage3DOnImage3D(target, ct)
    COM_coord = target.centerOfMass
    COM_index = target.getVoxelIndexFromPosition(COM_coord)
    Z_coord = COM_index[2]

    img_ct = ct.imageArray[:, :, Z_coord].transpose(1, 0)
    contourTargetMask = target.getBinaryContourMask()
    img_mask = contourTargetMask.imageArray[:, :, Z_coord].transpose(1, 0)
    img_dose = resampleImage3DOnImage3D(doseImage, ct)
    img_dose = img_dose.imageArray[:, :, Z_coord].transpose(1, 0)

    
    # Display dose
    fig, ax = plt.subplots(1, 2, figsize=(10, 5))
    ax[0].axes.get_xaxis().set_visible(False)
    ax[0].axes.get_yaxis().set_visible(False)
    ax[0].imshow(img_ct, cmap='gray')
    ax[0].imshow(img_mask, alpha=.2, cmap='binary')  # PTV
    dose = ax[0].imshow(img_dose, cmap='jet', alpha=.2)
    plt.colorbar(dose, ax=ax[0])
    ax[1].plot(dvh.histogram[0], dvh.histogram[1], label=dvh.name)
    ax[1].set_xlabel("Dose (Gy)")
    ax[1].set_ylabel("Volume (%)")
    ax[1].grid(True)
    ax[1].legend()
    plt.show()

if __name__ == "__main__":
    run(os.path.join(Path(os.getcwd()).parent.absolute(), 'opentps', 'testData','Phantom'))