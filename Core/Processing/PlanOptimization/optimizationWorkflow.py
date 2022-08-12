import logging

import numpy as np

from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planStructure import PlanStructure
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.sparseBeamlets import SparseBeamlets
from Core.IO import mcsquareIO, scannerReader
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing import resampler3D
from Core.Processing.PlanOptimization.Objectives.doseFidelity import DoseFidelity
from Core.Processing.PlanOptimization.planInitializer import PlanInitializer
from Core.Processing.PlanOptimization.planOptimization import IMPTPlanOptimizer
from Core.Processing.PlanOptimization.planOptimizationSettings import PlanOptimizationSettings
from programSettings import ProgramSettings


logger = logging.getLogger(__name__)


#TODO Do we really need objectives, beamlets and planStructure in plan
# Makes no sense that targetMask is defined in planStructure and objectives on targets are in plan
# Are planStructure and targetMask used outside this function?
# beamlets is used in planOptimization.py
# To me, beamlets should be given to planOptimization.py and removed from plan and objectives and objectives should be placed in planStructure.
# The definition of planStructure would be everything needed to build/optimize the plan.
# Si on fait comme ça, on peut sauver la planStructure et la reloader!

def optimizeIMPT(plan:RTPlan, planStructure:PlanStructure):
    plan.objectives.setScoringParameters(planStructure.ct)

    _defineTargetMaskAndPrescription(plan, planStructure)
    _createBeams(plan, planStructure)
    _initializeBeams(plan, planStructure)
    beamlets = _computeBeamlets(plan, planStructure)
    _optimizePlan(plan, beamlets)

    finalDose = _computeFinalDose(plan, beamlets, planStructure)
    finalDose.patient = plan.patient

def _defineTargetMaskAndPrescription(plan:RTPlan, planStructure:PlanStructure):
    from Core.Data.roiContour import ROIContour

    targetMask = None
    for objective in plan.objectives.fidObjList:
        if objective.metric == objective.Metrics.DMIN:
            roi = objective.roi

            plan.objectives.targetPrescription = objective.limitValue # TODO: User should enter this value

            if isinstance(roi, ROIContour):
                mask = roi.getBinaryMask(origin=objective.scoringOrigin, gridSize=objective.scoringGridSize,
                                              spacing=objective.scoringSpacing)
            elif isinstance(roi, ROIMask):
                mask = resampler3D.resampleImage3D(roi, gridSize=objective.scoringGridSize, spacing=objective.scoringSpacing,
                                                   origin=objective.scoringOrigin)
            else:
                raise Exception(roi.__class__.__name__ + ' is not a supported class for roi')

            if targetMask is None:
                targetMask = mask
            else:
                targetMask.imageArray = np.logical_or(targetMask.imageArray, mask.imageArray)

    if targetMask is None:
        raise Exception('Could not find a target volume in dose fidelity objectives')

    planStructure.targetMask = targetMask

def _createBeams(plan:RTPlan, planStructure:PlanStructure):
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

def _initializeBeams(plan:RTPlan, planStructure:PlanStructure):
    programSettings = ProgramSettings()
    ctCalibration = scannerReader.readScanner(programSettings.scannerFolder)

    initializer = PlanInitializer()
    initializer.ctCalibration = ctCalibration
    initializer.ct = planStructure.ct
    initializer.plan = plan
    initializer.targetMask = planStructure.targetMask
    initializer.initializePlan(planStructure.spotSpacing, planStructure.layerSpacing, planStructure.targetMargin)

def _computeBeamlets(plan:RTPlan, planStructure:PlanStructure):
    programSettings = ProgramSettings()
    optimizationSettings = PlanOptimizationSettings()

    bdl = mcsquareIO.readBDL(programSettings.bdlFile)
    ctCalibration = scannerReader.readScanner(programSettings.scannerFolder)

    mc2 = MCsquareDoseCalculator()
    mc2.ctCalibration = ctCalibration
    mc2.beamModel = bdl
    mc2.nbPrimaries = optimizationSettings.beamletPrimaries

    beamlets = mc2.computeBeamlets(planStructure.ct, plan)
    return beamlets

def _optimizePlan(plan:RTPlan, beamlets:SparseBeamlets):
    optimizationSettings = PlanOptimizationSettings()

    plan.beamlets = beamlets

    beamletMatrix = beamlets.toSparseMatrix()

    objectiveFunction = DoseFidelity(plan.objectives.fidObjList, beamletMatrix, formatArray=32, xSquare=False, scenariosBL=None, returnWorstCase=False)
    solver = IMPTPlanOptimizer(method=optimizationSettings.imptSolver, plan=plan, functions=[objectiveFunction], maxit=optimizationSettings.imptMaxIter)

    solver.xSquared = False

    w, doseImage, ps = solver.optimize()

    plan.spotMUs = w

def _computeFinalDose(plan:RTPlan, beamlets:SparseBeamlets, planStructure) -> DoseImage:
    beamlets.beamletWeights = plan.spotMUs
    return beamlets.toDoseImage()
