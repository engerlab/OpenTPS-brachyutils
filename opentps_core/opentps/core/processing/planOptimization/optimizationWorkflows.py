import logging
import time
import numpy as np

from opentps.core.data.images._doseImage import DoseImage
from opentps.core.data.images._roiMask import ROIMask
from opentps.core.data.plan._planIonBeam import PlanIonBeam
from opentps.core.data.plan._planDesign import PlanDesign
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.io import scannerReader, mcsquareIO
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.processing.imageProcessing import resampler3D
from opentps.core.processing.planOptimization.objectives.doseFidelity import DoseFidelity
from opentps.core.processing.planOptimization.planInitializer import PlanInitializer
from opentps.core.processing.planOptimization.planOptimization import IMPTPlanOptimizer
from opentps.core.processing.planOptimization.planOptimizationConfig import PlanOptimizationConfig

logger = logging.getLogger(__name__)

def optimizeIMPT(plan:RTPlan, planStructure:PlanDesign):
    """
    Optimizes an IMPT plan

    Parameters
    ----------
    plan : RTPlan
        The plan to be optimized
    planStructure : PlanDesign
        The plan design containing the optimization parameters
    """
    start = time.time()
    plan.planDesign = planStructure
    planStructure.objectives.setScoringParameters(planStructure.ct)

    _defineTargetMaskAndPrescription(planStructure)
    _createBeams(plan, planStructure)
    _initializeBeams(plan, planStructure)

    logger.info("New plan created in {} sec".format(time.time() - start))
    logger.info("Number of spots: {}".format(plan.numberOfSpots))

    _computeBeamlets(plan, planStructure)
    finalDose = _optimizePlan(plan, planStructure)

    finalDose.patient = plan.patient

def _defineTargetMaskAndPrescription(planStructure:PlanDesign):
    from opentps.core.data._roiContour import ROIContour

    targetMask = None
    for objective in planStructure.objectives.fidObjList:
        if objective.metric == objective.Metrics.DMIN:
            roi = objective.roi

            planStructure.objectives.targetPrescription = objective.limitValue # TODO: User should enter this value

            if isinstance(roi, ROIContour):
                mask = roi.getBinaryMask(origin=planStructure.ct.origin, gridSize=planStructure.ct.gridSize,
                                              spacing=planStructure.ct.spacing)
            elif isinstance(roi, ROIMask):
                mask = resampler3D.resampleImage3D(roi, origin=planStructure.ct.origin, gridSize=planStructure.ct.gridSize,
                                                   spacing=planStructure.ct.spacing)
            else:
                raise Exception(roi.__class__.__name__ + ' is not a supported class for roi')

            if targetMask is None:
                targetMask = mask
            else:
                targetMask.imageArray = np.logical_or(targetMask.imageArray, mask.imageArray)
            targetMask.patient = None

    if targetMask is None:
        raise Exception('Could not find a target volume in dose fidelity objectives')

    planStructure.targetMask = targetMask

def _createBeams(plan:RTPlan, planStructure:PlanDesign):
    for beam in plan:
        plan.removeBeam(beam)

    for i, gantryAngle in enumerate(planStructure.gantryAngles):
        beam = PlanIonBeam()
        beam.gantryAngle = gantryAngle
        beam.couchAngle = planStructure.couchAngles[i]
        beam.isocenterPosition = planStructure.targetMask.centerOfMass
        beam.id = i
        beam.name = 'B' + str(i)

        plan.appendBeam(beam)

def _initializeBeams(plan:RTPlan, planStructure:PlanDesign):
    dcConfig = DoseCalculationConfig()
    ctCalibration = scannerReader.readScanner(dcConfig.scannerFolder)

    initializer = PlanInitializer()
    initializer.ctCalibration = ctCalibration
    initializer.ct = planStructure.ct
    initializer.plan = plan
    initializer.targetMask = planStructure.targetMask
    initializer.initializePlan(planStructure.spotSpacing, planStructure.layerSpacing, planStructure.targetMargin)

def _computeBeamlets(plan:RTPlan, planStructure:PlanDesign):
    dcConfig = DoseCalculationConfig()
    optimizationSettings = PlanOptimizationConfig()

    bdl = mcsquareIO.readBDL(dcConfig.bdlFile)
    ctCalibration = scannerReader.readScanner(dcConfig.scannerFolder)

    mc2 = MCsquareDoseCalculator()
    mc2.ctCalibration = ctCalibration
    mc2.beamModel = bdl
    mc2.nbPrimaries = optimizationSettings.beamletPrimaries
    # TODO: specify scoring grid
    #mc2.independentScoringGrid = True

    planStructure.beamlets = mc2.computeBeamlets(planStructure.ct, plan)

def _optimizePlan(plan:RTPlan, planStructure:PlanDesign):
    optimizationSettings = PlanOptimizationConfig()

    beamletMatrix = planStructure.beamlets.toSparseMatrix()

    objectiveFunction = DoseFidelity(planStructure.objectives.fidObjList, beamletMatrix, xSquare=False, scenariosBL=None, returnWorstCase=False)
    solver = IMPTPlanOptimizer(optimizationSettings.imptSolver, plan, functions=[objectiveFunction], maxit=optimizationSettings.imptMaxIter)

    solver.xSquared = False

    doseImage, ps = solver.optimize()
    return doseImage
