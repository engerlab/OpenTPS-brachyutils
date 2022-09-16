from typing import Optional, Sequence, Union
import opentps
import os
import numpy as np
np.random.seed(42)
import random
random.seed(42)
from Core.Data.DynamicData.dynamic3DModel import Dynamic3DModel
from Core.Data.DynamicData.dynamic3DSequence import Dynamic3DSequence
from Core.Data.Plan._rtPlan import RTPlan
from Core.IO import mcsquareIO
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Utils.programSettings import ProgramSettings
from pydicom.uid import generate_uid
from Core.Data.CTCalibrations.MCsquareCalibration._mcsquareCTCalibration import MCsquareCTCalibration
from Core.Data._rtStruct import ROIContour
from Core.Data.Images._doseImage import DoseImage
from Core.IO.dicomIO import readDicomDose, writeRTDose
from Core.Processing.PlanDeliverySimulation.beamDeliveryTimings import BDT
import time

def simulate_4DD(plan: RTPlan, CT4D: Dynamic3DSequence, model3D: Dynamic3DModel = None, simulation_dir: str = None, crop_contour=None):
    """
    4D dose computation (range variation - no interplay) where one treatment is simulated on 4DCT
    """
    if simulation_dir is None:
        simulation_dir = os.path.join(ProgramSettings().simulationFolder, 'plan_delivery_simulations')
    if not os.path.exists(simulation_dir): os.mkdir(simulation_dir)
    if model3D is None:
        model3D = Dynamic3DModel()
        model3D.name = 'MidP'
        model3D.seriesInstanceUID = generate_uid()
        model3D.computeMidPositionImage(CT4D, tryGPU=True)

    dir_4DD = os.path.join(simulation_dir, '4DD')
    fx_dir = os.path.join(dir_4DD, f'{plan.numberOfFractionsPlanned}_fx')
    if not os.path.exists(dir_4DD):
        os.mkdir(dir_4DD)
    if not os.path.exists(fx_dir):
        os.mkdir(fx_dir)

    compute_dose_on_each_phase(plan, CT4D, fx_dir, crop_contour=crop_contour)
    output_accumulated_dose = os.path.join(fx_dir, "dose_accumulated_4DD.dcm")
    accumulate_dose_from_different_phases(fx_dir, model3D, output_accumulated_dose, divide_total_dose=True, dose_name='4DD Accumulated dose')


def simulate_4DDD(plan: RTPlan, CT4D: Dynamic3DSequence, model3D: Dynamic3DModel = None, simulation_dir: str = None, crop_contour=None, save_partial_doses=True, start_phase=0):
    """
    4D dynamic dose computation (range variation + interplay) where one treatment is simulated on 4DCT
    """
    if len(plan.spotTimings)==0:
        print('Plan has no delivery timings. Querying ScanAlgo...')
        bdt = BDT(plan)
        plan = bdt.getPBSTimings(sort_spots="true")
    # plan.simplify()

    if simulation_dir is None:
        simulation_dir = os.path.join(ProgramSettings().simulationFolder, 'plan_delivery_simulations')
    if not os.path.exists(simulation_dir): os.mkdir(simulation_dir)
    if model3D is None:
        model3D = Dynamic3DModel()
        model3D.name = 'MidP'
        model3D.seriesInstanceUID = generate_uid()
        model3D.computeMidPositionImage(CT4D, tryGPU=True)
        
    dir_4DDD = os.path.join(simulation_dir, '4DDD')
    fx_dir = os.path.join(dir_4DDD, f'{plan.numberOfFractionsPlanned}_fx')
    if not os.path.exists(dir_4DDD):
        os.mkdir(dir_4DDD)
    if not os.path.exists(fx_dir):
        os.mkdir(fx_dir)
    
    # for start_phase in range(number_of_starting_phases):
    plan_4DCT = split_plan_to_phases(plan, num_plans=len(CT4D), start_phase=start_phase)
    path_dose = os.path.join(fx_dir, f'starting_phase_{start_phase}')
    if not os.path.exists(path_dose):
        os.mkdir(path_dose)
    compute_dose_on_each_phase(plan_4DCT, CT4D, path_dose, crop_contour=crop_contour)
    acc_filename = 'dose_accumulated.dcm'
    acc_path = os.path.join(path_dose, acc_filename)
    accumulate_dose_from_different_phases(path_dose, model3D, acc_path, dose_name=f'4DDD accumulated dose - starting phase p{start_phase}')
    print(f"4DDD simulation done for starting phase {start_phase}")
    if not save_partial_doses:
        for f in os.listdir(path_dose):
            if f != acc_filename: os.remove(os.path.join(path_dose, f))


def simulate_4DDD_scenarios(plan: RTPlan, CT4D: Dynamic3DSequence, model3D: Dynamic3DModel = None, 
        simulation_dir: str = None, crop_contour=None, save_partial_doses=True, number_of_fractions=1, 
        number_of_starting_phases=1, number_of_fractionation_scenarios=1):
    """
    Simulate treatment with fraction number of fractions where num_scenarios MidP dose are accumulated on the MidP.
    A scenario consist of a 1 fraction simulation with a random starting phase (with replacement)
    """
    plan.numberOfFractionsPlanned = number_of_fractions
    number_of_phases = len(CT4D)
    if number_of_starting_phases>number_of_phases:
        print(f"Number of starting phases must be smaller or equal to number of phases in 4DCT. Changing it to {number_of_phases}")
        number_of_starting_phases = number_of_phases
    if number_of_fractions==1 and number_of_fractionation_scenarios>1:
        print('There can only be one fractionation scenario when the number of fractions is 1.')
        return

    if simulation_dir is None:
        simulation_dir = os.path.join(ProgramSettings().simulationFolder, 'plan_delivery_simulations')
    if not os.path.exists(simulation_dir): os.mkdir(simulation_dir)
    dir_4DDD = os.path.join(simulation_dir, '4DDD')
    fx_dir = os.path.join(dir_4DDD, f'{number_of_fractions}_fx')
    dir_scenarios = os.path.join(fx_dir, 'scenarios')
    if not os.path.exists(dir_4DDD):
        os.mkdir(dir_4DDD)
    if not os.path.exists(fx_dir):
        os.mkdir(fx_dir)
    if not os.path.exists(dir_scenarios):
        os.mkdir(dir_scenarios)

    # 4DDD simulation
    for start_phase in range(number_of_starting_phases):
        if not os.exists(os.path.join(fx_dir, f'starting_phase_{start_phase}')):
            simulate_4DDD(plan, CT4D, model3D, simulation_dir, crop_contour, save_partial_doses, start_phase)

    path_to_accumulated_doses = [os.path.join(fx_dir, start_phase_dir, 'dose_accumulated.dcm') for start_phase_dir in sorted(os.listdir(fx_dir)) if start_phase_dir != 'scenarios']
    for scenario_number in range(number_of_fractionation_scenarios):
        dose_files = random_combination_with_replacement(path_to_accumulated_doses, number_of_fractionation_scenarios)
        output_path = os.path.join(dir_scenarios, f'dose_scenario_{str(scenario_number)}.dcm')
        accumulate_dose_from_same_phase(dose_files, model3D.midp, output_path, number_of_fractions=number_of_fractions, dose_name=f'dose {number_of_fractions}fx scenario {str(scenario_number)}')


def split_plan_to_phases(ReferencePlan: RTPlan, num_plans=10, breathing_period=4., start_phase=0):
    """
    Split spots from plan to num_plans plans according to the number of images in 4DCT, breathing period and start phase.
    Return a list of num_plans plans where each spot is assigned to a plan (=breathing phase)
    """
    time_per_phase = breathing_period / num_plans

    # Rearrange order of list CT4D to start at start_phase
    phase_number = np.append(np.arange(start_phase,num_plans), np.arange(0,start_phase))

    # Initialize plan for each image of the 4DCT
    plan_4DCT = {}
    for p in phase_number:
        plan_4DCT[p] = ReferencePlan.createEmptyPlanWithSameMetaData()
        plan_4DCT[p].name = f"plan_phase_{p}"

    # Assign each spot to a phase depending on its timing
    num_beams = len(ReferencePlan.beams)
    for b in range(num_beams):
        beam = ReferencePlan.beams[b]
        current_beam_phase_offset = np.random.randint(num_plans) if b>0 else 0 # beams should start at different times
        print('current_beam_phase_offset',current_beam_phase_offset)
        for layer in beam.layers:
            # Assing each spot
            for s in range(len(layer.spotMUs)):
                phase = int((layer.spotTimings[s] % breathing_period) // time_per_phase)
                phase = (phase + current_beam_phase_offset) % num_plans
                plan_4DCT[phase_number[phase]].appendSpot(beam, layer, s)

    return plan_4DCT


def compute_dose_on_each_phase(plans:Union[RTPlan, dict], CT4D:Dynamic3DSequence, output_path:str, crop_contour:ROIContour=None):
    """
    Compute and save doses simulated on each 3DCT image of path_4DCT
    In case plans is a RTplan, the same plan is simulated on each 3DCT (4DD case)
    In case plans is a list, len(plans)==len(path_4DCT) and each plans is computed on the 3DCT image (4DDD)
    INPUT:
        plans: either a RTplan object or a dictionnary of RTplans
        path_4DCT: list of 3DCT paths
        output_path: folder path to save doses
        crop_contour: contour name for on which we crop the CT (None if not applicable)
    """
    if type(plans) is dict:
        assert len(plans)==len(CT4D)
        plan_names = list(plans.keys())
        dose_prefix = "partial_dose_phase"
    elif type(plans) is RTPlan:
        dose_prefix = "total_dose_phase"
    else:
        raise Exception('plans must be a dict or a RTplan object')

    current_plan = plans
    for p in range(len(CT4D)):
        # Import CT
        CT = CT4D.dyn3DImageList[p]

        # Plan
        if type(plans) is dict:
            current_plan = plans[plan_names[p]]

        # Create MCsquare simulation
        mc2 = initialize_MCsquare_params()
        if crop_contour is not None:
            mc2.overwriteOutsideROI = crop_contour
        dose = mc2.computeDose(CT, current_plan)
        writeRTDose(dose, os.path.join(output_path, f"{dose_prefix}{p:03d}.dcm"))


def initialize_MCsquare_params(workdir=None, scannerName = 'UCL_Toshiba', beamModelFile = 'UMCG_P1_v2_RangeShifter.txt'):
    mc2 = MCsquareDoseCalculator()
    if workdir is not None:
      mc2.simulationDirectory = workdir
    MCSquarePath = os.path.join(os.path.split(opentps.__file__)[0], 'Core', 'Processing', 'DoseCalculation', 'MCsquare')
    beamModel = mcsquareIO.readBDL(os.path.join(MCSquarePath, 'BDL', beamModelFile))
    mc2.beamModel = beamModel
    scannerPath = os.path.join(MCSquarePath, 'Scanners', scannerName)
    calibration = MCsquareCTCalibration(fromFiles=(os.path.join(scannerPath, 'HU_Density_Conversion.txt'),
                                                os.path.join(scannerPath, 'HU_Material_Conversion.txt'),
                                                os.path.join(MCSquarePath, 'Materials')))
    mc2.ctCalibration = calibration
    mc2.nbPrimaries = 1e7
    return mc2


def accumulate_dose_from_different_phases(dose_4DCT_path:str, model3D: Dynamic3DModel, output_path:str, divide_total_dose=False, dose_name='Accumulated dose'):
    """
    Accumulate partial doses from 4DCT on reference image MidPCT via deformable registration according to deformation fields df_phase_to_ref_path
    """
    
    dose_files = []
    if type(dose_4DCT_path) is list:
        dose_files = dose_4DCT_path
    else:
        for file in os.listdir(dose_4DCT_path):
            # if file.startswith("dose_phase"):
            if 'accumulated' not in file:
                dose_files.append(os.path.join(dose_4DCT_path,file))
    dose_files.sort()

    assert len(dose_files)==len(model3D.deformationList)

    # Initialize reference dose on the MidP image
    dose_MidP = DoseImage().createEmptyDoseWithSameMetaData(model3D.midp)
    dose_MidP.name = dose_name

    for i in range(len(dose_files)):
        # Load dose on 3D image
        print(f"Importing dose {dose_files[i]}")
        dose = readDicomDose(dose_files[i])

        # Load deformation field on 3D image
        df = model3D.deformationList[i]

        start = time.time()
        # Apply deformation field and accumulate on MidP
        if divide_total_dose:
            dose._imageArray /= len(dose_files)
            dose_MidP._imageArray += df.deformImage(dose)._imageArray
        else:
            dose_MidP._imageArray += df.deformImage(dose)._imageArray
        end = time.time()
        print(f"dose deformed in {end-start} sec")

    writeRTDose(dose_MidP, output_path)


def accumulate_dose_from_same_phase(dose_4DCT_path, MidPCT, output_path, number_of_fractions=1, dose_name='Accumulated dose'):
    """ Same function as accumulate_dose_from_different_phases but from doses from the same phase
    i.e. no deformable registration needed"""
    dose_files = dose_4DCT_path
    dose_files.sort()

    # Initialize reference dose on the MidP image
    dose_MidP = DoseImage().createEmptyDoseWithSameMetaData(MidPCT)
    dose_MidP.name = dose_name

    for i in range(len(dose_files)):
        # Load dose on 3D image
        print(f"Importing dose {dose_files[i]}")
        dose = readDicomDose(dose_files[i])

        # Accumulate on MidP
        dose_MidP._imageArray += dose._imageArray

    dose_MidP._imageArray /= number_of_fractions
    writeRTDose(dose_MidP, output_path)


def random_combination_with_replacement(iterable, r):
    """Random selection from itertools.combinations_with_replacement(iterable, r)
    Taken from https://docs.python.org/3/library/itertools.html#itertools-recipes
    """
    pool = tuple(iterable)
    n = len(pool)
    indices = random.choices(range(n), k=r)
    return [pool[i] for i in indices]

