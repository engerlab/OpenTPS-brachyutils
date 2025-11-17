
import os
import logging
import numpy as np
import sys
import scipy as sp

from opentps.core.processing.planOptimization.planOptimization import IntensityModulationOptimizer
from matplotlib import pyplot as plt
from opentps.core.data.images import CTImage
from opentps.core.data.images import ROIMask
from opentps.core.data import DVH
from opentps.core.data import Patient
from opentps.core.data.plan import FidObjective
from opentps.core.data.plan import RobustnessPhoton
from opentps.core.io import mcsquareIO
from opentps.core.io.scannerReader import readScanner
from opentps.core.io.serializedObjectIO import loadRTPlan, saveRTPlan
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.imageProcessing.resampler3D import resampleImage3DOnImage3D
from opentps.core.processing.doseCalculation.photons.cccDoseCalculator import CCCDoseCalculator
from opentps.core.data.plan import PhotonPlanDesign
import copy
from scipy.sparse import csc_matrix
from opentps.core.io.dicomIO import writeRTDose
sys.path.append('..')

logger = logging.getLogger(__name__)

# Generic example: box of water with squared target
def run(output_path=""):
    if(output_path != ""):
        output_path = output_path
    else:
        output_path = os.path.join(os.getcwd(), 'Photon_Robust_Output_Example')
        if not os.path.exists(output_path):
            os.makedirs(output_path)
    logger.info('Files will be stored in {}'.format(output_path))

    ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)

    patient = Patient()
    patient.name = 'Patient'

    ctSize = 150

    ct = CTImage()
    ct.name = 'CT'
    ct.patient = patient
    
    huAir = -1024.
    huWater = 0
    data = huAir * np.ones((ctSize, ctSize, ctSize))
    data[:, 50:, :] = huWater
    ct.imageArray = data

    roi = ROIMask()
    roi.patient = patient
    roi.name = 'TV'
    roi.color = (255, 0, 0)  # red
    data = np.zeros((ctSize, ctSize, ctSize)).astype(bool)
    data[100:120, 100:120, 100:120] = True
    roi.imageArray = data

    # Design plan
    beamNames = ["Beam1", "Beam2"]
    gantryAngles = [0., 90.]
    couchAngles = [0.,0]

    # Create output folder
    if not os.path.isdir(output_path):
        os.mkdir(output_path)

    ## Dose computation from plan
    ccc = CCCDoseCalculator(batchSize= 30)
    ccc.ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)


    # Load / Generate new plan
    plan_file = os.path.join(output_path, "RobustPlan_notCropped.tps")

    if os.path.isfile(plan_file):
        plan = loadRTPlan(plan_file, 'photon')
        logger.info('Plan loaded')
    else:
        planDesign = PhotonPlanDesign()
        planDesign.ct = ct
        planDesign.targetMask = roi
        planDesign.gantryAngles = gantryAngles
        planDesign.beamNames = beamNames
        planDesign.couchAngles = couchAngles
        planDesign.calibration = ctCalibration
        planDesign.xBeamletSpacing_mm = 4
        planDesign.yBeamletSpacing_mm = 4

        # Robustness settings
        planDesign.robustness = RobustnessPhoton()
        planDesign.robustness.setupSystematicError = [4, 4, 4] # mm
        planDesign.robustness.setupRandomError = None # Random error can not be include in the optimization. But well in evaluation.
        
        # Strategy selection 
        planDesign.robustness.selectionStrategy = planDesign.robustness.Strategies.REDUCED_SET
        # planDesign.robustness.selectionStrategy = planDesign.robustness.Strategies.ALL
        # planDesign.robustness.selectionStrategy = planDesign.robustness.Strategies.RANDOM
        # planDesign.robustness.numScenarios = 10   # specify how many random scenarios to simulate, default = 100

        planDesign.targetMargin = max(planDesign.robustness.setupSystematicError) * 2.5 + max(planDesign.xBeamletSpacing_mm, planDesign.yBeamletSpacing_mm) # sigma * number of sigma (95%)
        planDesign.defineTargetMaskAndPrescription(target = roi, targetPrescription = 20.) # needs to be called prior spot placement
        plan = planDesign.buildPlan()  # Spot placement
        plan.PlanName = "RobustPlan"

        nominal, scenarios = ccc.computeRobustScenarioBeamlets(ct, plan, robustMode='Shift') # 'Simulation' for total recomputation
        plan.planDesign.beamlets = nominal
        plan.planDesign.robustness.scenarios = scenarios
        plan.planDesign.robustness.numScenarios = len(scenarios)
        
    saveRTPlan(plan, plan_file, unloadBeamlets=False)
    plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMAX, 20.0, 1.0, robust=True)
    plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMIN, 20.5, 1.0, robust=True)

    plan.planDesign.ROI_cropping = False # Do not cropped allows 'shift' evaluation method to be used
    solver = IntensityModulationOptimizer(method='Scipy_L-BFGS-B', plan=plan, maxiter=50)
    # Optimize treatment plan
    doseInfluenceMatrix = copy.deepcopy(plan.planDesign.beamlets)
    doseImage, ps = solver.optimize()

    # User input filename
    # writeRTDose(doseImage, output_path, outputFilename="BeamletTotalDose")
    # or default name
    writeRTDose(doseImage, output_path)

    if plan.planDesign.ROI_cropping == True :
        plan_file = os.path.join(output_path, "Plan_Photon_WaterPhantom_cropped_optimized.tps")
    else : 
        plan_file = os.path.join(output_path, "Plan_Photon_WaterPhantom_notCropped_optimized.tps")

    saveRTPlan(plan, plan_file, unloadBeamlets=False)

    # Compute DVH
    target_DVH = DVH(roi, doseImage)
    print('D95 = ' + str(target_DVH.D95) + ' Gy')
    print('D5 = ' + str(target_DVH.D5) + ' Gy')
    print('D5 - D95 =  {} Gy'.format(target_DVH.D5 - target_DVH.D95))

    # center of mass
    roi = resampleImage3DOnImage3D(roi, ct)
    COM_coord = roi.centerOfMass
    COM_index = roi.getVoxelIndexFromPosition(COM_coord)
    Z_coord = COM_index[2]

    img_ct = ct.imageArray[:, :, Z_coord].transpose(1, 0)
    contourTargetMask = roi.getBinaryContourMask()
    img_mask = contourTargetMask.imageArray[:, :, Z_coord].transpose(1, 0)
    img_dose = resampleImage3DOnImage3D(doseImage, ct)
    img_dose = img_dose.imageArray[:, :, Z_coord].transpose(1, 0)

    # Display dose
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    ax[0].axes.get_xaxis().set_visible(False)
    ax[0].axes.get_yaxis().set_visible(False)
    ax[0].imshow(img_ct, cmap='gray')
    ax[0].imshow(img_mask, alpha=.2, cmap='binary')  # PTV
    dose = ax[0].imshow(img_dose, cmap='jet', alpha=.2)
    plt.colorbar(dose, ax=ax[0])
    ax[1].plot(target_DVH.histogram[0], target_DVH.histogram[1], label=target_DVH.name)
    ax[1].set_xlabel("Dose (Gy)")
    ax[1].set_ylabel("Volume (%)")
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join(output_path, 'Dose_RobustOptimizationPhotons.png'))
    plt.show()

if __name__ == "__main__":
    run()
