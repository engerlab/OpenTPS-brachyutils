import numpy as np
import os
import time
import datetime

from matplotlib import pyplot as plt

from opentps.core.data.images import CTImage
from opentps.core.data.images import ROIMask
from opentps.core.data.plan import ObjectivesList
from opentps.core.data.plan import PlanDesign
from opentps.core.data import DVH
from opentps.core.data import Patient
from opentps.core.data.plan import FidObjective
from opentps.core.io import mcsquareIO
from opentps.core.io.dataLoader import readData
from opentps.core.io.scannerReader import readScanner
from opentps.core.io.serializedObjectIO import saveRTPlan, loadRTPlan
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.processing.imageProcessing.resampler3D import resampleImage3DOnImage3D
from opentps.core.processing.planOptimization.tools import evaluateClinical


def run():
    ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)
    bdl = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)

    # Patient
    ctImagePath = "/home/sophie/opentps/data/Plan_IMPT_patient1"
    dataList = readData(ctImagePath, maxDepth=0)
    print(dataList)
    ct = dataList[5]
    contours = dataList[4]
    print('Available ROIs')
    contours.print_ROINames()

    output_path = os.path.join(ctImagePath,'OpenTPS')
    if not os.path.isdir(output_path):
        os.mkdir(output_path)
    print('Files will be stored in ' + output_path)

    # ROIs
    target = contours.getContourByName('CTV')
    targetMask = target.getBinaryMask(origin=ct.origin, gridSize=ct.gridSize, spacing=ct.spacing)
    opticChiasm = contours.getContourByName('Optic Chiasm')
    brainStem = contours.getContourByName('Brain Stem')
    brain = contours.getContourByName('Brain')
    body = contours.getContourByName('BODY')
    lon  = contours.getContourByName('LON')
    ron  = contours.getContourByName('RON')

    # create rings
    rings = targetMask.createMaskRings(3,1)


    # Configure MCsquare
    mc2 = MCsquareDoseCalculator()
    mc2.beamModel = bdl
    mc2.ctCalibration = ctCalibration
    mc2.nbPrimaries = 2e7

    # Load / Generate new plan
    #plan_file = os.path.join(output_path, "Plan_blfree_refactor_.tps")
    #plan_file = os.path.join(output_path, "Plan_BLfree_SS4_LS4_RTV6refactor_Nov-14-2022_11-52-48_Brain_BLfree_SS4_LS4_RTV6_refactor.tps")
    plan_file = os.path.join(output_path, "iPlan_BLfree_SS4_LS4_RTV7refactor_Nov-15-2022_09-49-47_Brain_BLfree_SS4_LS4_RTV7_refactor.tps")
    
    spotSpacing = 4
    layerSpacing = 4
    targetMargin = 7

    if os.path.isfile(plan_file):
        plan = loadRTPlan(plan_file)
        print('Plan loaded')
    else:
        # Design plan
        beamNames = ["Beam1", "Beam2","Beam3"]
        gantryAngles = [90.,90,90.]
        couchAngles = [0.,270.,315.]

        # Generate new plan

        start_init = time.time()
        planInit = PlanDesign()
        planInit.ct = ct
        planInit.targetMask = targetMask
        planInit.gantryAngles = gantryAngles
        planInit.beamNames = beamNames
        planInit.couchAngles = couchAngles
        planInit.calibration = ctCalibration
        planInit.spotSpacing = spotSpacing
        planInit.layerSpacing = layerSpacing
        planInit.targetMargin = targetMargin

        plan = planInit.buildPlan()  # Spot placement
        plan.PlanName = "BLfree_SS" + str(spotSpacing) + "_LS" + str(layerSpacing) + "_RTV" + str(targetMargin) + "refactor"


    plan.planDesign.objectives = ObjectivesList()
    plan.planDesign.objectives.setTarget(target.name, 65.0)
    plan.planDesign.objectives.fidObjList = []
    plan.planDesign.objectives.addFidObjective(target, FidObjective.Metrics.DMAX, 65.0, 5.0)
    plan.planDesign.objectives.addFidObjective(target, FidObjective.Metrics.DMIN, 65.5, 5.0)
    plan.planDesign.objectives.addFidObjective(opticChiasm, FidObjective.Metrics.DMAX, 60.0, 1.0)
    #plan.planDesign.objectives.addFidObjective(brain, FidObjective.Metrics.DMAX, 65.0, 1.0)
    plan.planDesign.objectives.addFidObjective(brainStem, FidObjective.Metrics.DMAX, 55.0, 1.0)
    plan.planDesign.objectives.addFidObjective(lon, FidObjective.Metrics.DMAX, 39.0, 1.0)
    plan.planDesign.objectives.addFidObjective(ron, FidObjective.Metrics.DMAX, 37.0, 1.0)
    plan.planDesign.objectives.addFidObjective(rings[0], FidObjective.Metrics.DMAX, 65.0, 1.0)
    plan.planDesign.objectives.addFidObjective(rings[1], FidObjective.Metrics.DMAX, 60.0, 1.0)
    plan.planDesign.objectives.addFidObjective(rings[2], FidObjective.Metrics.DMAX, 55.0, 1.0)
   
    try:
        end_init = time.time() - start_init
    except:
        end_init = 0
        
    start_opti = time.time() 
    # MCsquare beamlet free planOptimization
    dose = mc2.optimizeBeamletFree(ct, plan, [target, opticChiasm, brain, brainStem, lon, ron, rings[0], rings[1], rings[2]])
    end_opti = time.time() - start_opti

    print("============================================================")
    print("Running time")
    print("Plan creation = {:.2f} s ".format(end_init))
    print("Optimization = {:.2f} s".format(end_opti))
    print("Total optimization = {:.2f} s".format(end_init + end_opti))
    print("============================================================")
    
    plan_file = os.path.join(output_path, "Plan_" + plan.PlanName + "_" + datetime.datetime.today().strftime("%b-%d-%Y_%H-%M-%S") + "_Brain_BLfree_SS" + str(spotSpacing) + "_LS" + str(layerSpacing) + "_RTV" + str(targetMargin) + "_refactor.tps") 
    saveRTPlan(plan, plan_file)

    # Compute DVH
    target_DVH = DVH(target, dose)
    D50 = target_DVH.D50
    # scale dose
    dose.imageArray = dose.imageArray * (plan.planDesign.objectives.targetPrescription)/D50
    
    target_DVH = DVH(target, dose)
    chiasm_DVH = DVH(opticChiasm, dose)
    stem_DVH = DVH(brainStem, dose)
    lon_DVH = DVH(lon, dose)
    ron_DVH = DVH(ron, dose)
    
    print('D95 = ' + str(target_DVH.D95) + ' Gy')
    print('D5 = ' + str(target_DVH.D5) + ' Gy')
    print('D5 - D95 =  {} Gy'.format(target_DVH.D5 - target_DVH.D95))
    print("============================================================")

    # clinical evaluation

    clinROI = [target.name, target.name, opticChiasm.name, opticChiasm.name, brainStem.name, brainStem.name, ron.name, lon.name, ron.name, lon.name, body.name] 
    clinMetric = ["Dmin", "Dmax",  "Dmax", "Dmean", "Dmax", "Dmean", "Dmax", "Dmax", "Dmean", "Dmean", "Dmax"]
    clinLimit = [61.75, 68.25, 60., 50., 55., 8.5, 39., 37., 4., 4.25, 65.]
    clinObj = {}
    clinObj['ROI'] = clinROI
    clinObj['Metric'] = clinMetric
    clinObj['Limit'] = clinLimit
    
    print('Beamlet-free: Clinical evaluation')
    evaluateClinical(dose, contours, clinObj)
    
    
    
    # center of mass
    COM_coord = targetMask.centerOfMass
    COM_index = targetMask.getVoxelIndexFromPosition(COM_coord)
    Z_coord = COM_index[2]
    
    img_ct = ct.imageArray[:, :, Z_coord].transpose(1, 0)
    contourTargetMask = target.getBinaryContourMask(origin=ct.origin, gridSize=ct.gridSize, spacing=ct.spacing)
    img_mask = contourTargetMask.imageArray[:, :, Z_coord].transpose(1, 0)
    img_dose = dose.imageArray[:, :, Z_coord].transpose(1, 0)
    
    # Display dose
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    ax[0].axes.get_xaxis().set_visible(False)
    ax[0].axes.get_yaxis().set_visible(False)
    ax[0].imshow(img_ct, cmap='gray')
    ax[0].imshow(img_mask, alpha=.2, cmap='binary')  
    dose = ax[0].imshow(img_dose, cmap='jet', alpha=.2)
    plt.colorbar(dose, ax=ax[0])
    ax[1].plot(target_DVH.histogram[0], target_DVH.histogram[1], label=target_DVH.name)
    ax[1].plot(chiasm_DVH.histogram[0], chiasm_DVH.histogram[1], label=chiasm_DVH.name)
    ax[1].plot(stem_DVH.histogram[0], stem_DVH.histogram[1], label=stem_DVH.name)
    ax[1].plot(lon_DVH.histogram[0], lon_DVH.histogram[1], label=lon_DVH.name)
    ax[1].plot(ron_DVH.histogram[0], ron_DVH.histogram[1], label=ron_DVH.name)
    ax[1].set_xlabel("Dose (Gy)")
    ax[1].set_ylabel("Volume (%)")
    plt.grid(True)
    plt.legend()
    
    plt.show()

if __name__ == "__main__":
    run()
