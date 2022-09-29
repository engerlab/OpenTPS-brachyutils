
import os
import sys

sys.path.append('..')
import numpy as np
from matplotlib import pyplot as plt
from opentps.core.data.images import CTImage
from opentps.core.data.images import ROIMask
from opentps.core.data.plan import ObjectivesList
from opentps.core.data.plan import PlanDesign
from opentps.core.data import DVH
from opentps.core.data import Patient
from opentps.core.data.plan import FidObjective
from opentps.core.io import mcsquareIO
from opentps.core.io.scannerReader import readScanner
from opentps.core.io.serializedObjectIO import loadRTPlan, saveRTPlan
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.processing.imageProcessing.resampler3D import resampleImage3DOnImage3D
from opentps.core.processing.planOptimization.planOptimization import IMPTPlanOptimizer

# Generic example: box of water with squared target
def run():
    output_path = os.getcwd()
    print('Files will be stored in ' + output_path)


    ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)
    bdl = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)

    patient = Patient()
    patient.name = 'Patient'

    ctSize = 150

    ct = CTImage()
    ct.name = 'CT'
    ct.patient = patient

    huAir = -1024.
    huWater = ctCalibration.convertRSP2HU(1.)
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
    beamNames = ["Beam1"]
    gantryAngles = [0.]
    couchAngles = [0.]

    # Create output folder
    if not os.path.isdir(output_path):
        os.mkdir(output_path)

    # Configure MCsquare
    mc2 = MCsquareDoseCalculator()
    mc2.beamModel = bdl
    mc2.nbPrimaries = 5e4
    mc2.ctCalibration = ctCalibration
    mc2.setupSystematicError = [5.0, 5.0, 5.0]  # mm
    mc2.setupRandomError = [0.0, 0.0, 0.0]  # mm (sigma)
    mc2.rangeSystematicError = 3.0  # %
    mc2.robustnessStrategy = "ErrorSpace_regular"

    # Load / Generate new plan
    plan_file = os.path.join(output_path, "RobustPlan_notCropped.tps")

    if os.path.isfile(plan_file):
        plan = loadRTPlan(plan_file)
    else:
        planInit = PlanDesign()
        planInit.ct = ct
        planInit.targetMask = roi
        planInit.gantryAngles = gantryAngles
        planInit.beamNames = beamNames
        planInit.couchAngles = couchAngles
        planInit.calibration = ctCalibration
        planInit.spotSpacing = 7.0
        planInit.layerSpacing = 6.0
        planInit.targetMargin = max(planInit.spotSpacing, planInit.layerSpacing) + max(mc2.setupSystematicError)

        plan = planInit.buildPlan()  # Spot placement
        plan.PlanName = "RobustPlan"

        nominal, scenarios = mc2.computeRobustScenarioBeamlets(ct, plan, roi=[roi], storePath=output_path)
        plan.planDesign.beamlets = nominal
        plan.planDesign.scenarios = scenarios
        plan.planDesign.numScenarios = len(scenarios)

        #saveRTPlan(plan, plan_file)



    beamletMatrix = plan.planDesign.beamlets.toSparseMatrix()
    saveRTPlan(plan, plan_file)
    plan.planDesign.objectives = ObjectivesList()
    plan.planDesign.objectives.setTarget(roi.name, 20.0)
    plan.planDesign.objectives.setScoringParameters(ct)
    # scoringGridSize = [int(math.floor(i / j * k)) for i, j, k in zip(ct.gridSize, scoringSpacing, ct.spacing)]
    # plan.planDesign.objectives.setScoringParameters(ct, scoringGridSize, scoringSpacing)
    plan.planDesign.objectives.fidObjList = []
    plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMAX, 20.0, 1.0, robust=True)
    plan.planDesign.objectives.addFidObjective(roi, FidObjective.Metrics.DMIN, 20.5, 1.0, robust=True)

    solver = IMPTPlanOptimizer(method='Scipy-LBFGS', plan=plan, maxit=50)
    # Optimize treatment plan
    w, doseImage, ps = solver.optimize()

    # MCsquare simulation
    # mc2.nbPrimaries = 1e6
    # doseImage = mc2.computeDose(ct, plan)

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

    plt.show()

if __name__ == "__main__":
    run()