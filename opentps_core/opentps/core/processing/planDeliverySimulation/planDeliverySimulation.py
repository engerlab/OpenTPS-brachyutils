import re
from typing import Union
import os
import numpy as np
np.random.seed(42)
import random
random.seed(42)
from opentps.core.data.dynamicData.dynamic3DModel import Dynamic3DModel
from opentps.core.data.dynamicData.dynamic3DSequence import Dynamic3DSequence
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.data.images._ctImage import CTImage
from opentps.core.io import mcsquareIO
from opentps.core.processing.doseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from opentps.core.utils.programSettings import ProgramSettings
from pydicom.uid import generate_uid
from opentps.core.data._rtStruct import ROIContour
from opentps.core.data.images._doseImage import DoseImage
from opentps.core.io.dicomIO import readDicomDose, writeRTDose
from opentps.core.processing.planDeliverySimulation.beamDeliveryTimings import BDT
from opentps.core.io.scannerReader import readScanner
from opentps.core.io.dataLoader import readSingleData
from opentps.core.processing.doseCalculation.doseCalculationConfig import DoseCalculationConfig
from opentps.core.data.images._deformation3D import Deformation3D
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
        print('plan has no delivery timings. Querying ScanAlgo...')
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
    4D dynamic simulation under different scenarios

    Parameters
    ----------
    plan : RTPlan
    CT4D : Dynamic3DSequence
    model3D : Dynamic3DModel
    simulation_dir : str
        Path to the simulation direcrotry where the doses are saved
    crop_contour : ROIContour
        Overwrite values outside crop_contour
    save_partial_doses: bool
        Whether or not to save partial doses, i.e. doses on each phase before accumulation
    number_of_fractions: int
        Number of fractions for delivering the treatment
    number_of_starting_phases: int
        Number of times we simulate the delivery where each time with start from a different phase.
        Hence, number_of_starting_phases <= len(4DCT)
    number_of_fractionation_scenarios: int
        Number fractionation scenarios. For instance, if number_of_fractions=5 and number_of_fractionation_scenarios=3;
        Simulate 3 scenarios with starting phases [1,2,3,4,5]; [1,3,1,2,4]; [4, 5, 1, 4, 2].
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
        if not os.path.exists(os.path.join(fx_dir, f'starting_phase_{start_phase}')):
            simulate_4DDD(plan, CT4D, model3D, simulation_dir, crop_contour, save_partial_doses, start_phase)

    path_to_accumulated_doses = [os.path.join(fx_dir, start_phase_dir, 'dose_accumulated.dcm') for start_phase_dir in sorted(os.listdir(fx_dir)) if start_phase_dir != 'scenarios']
    for scenario_number in range(number_of_fractionation_scenarios):
        dose_files = random_combination_with_replacement(path_to_accumulated_doses, number_of_fractionation_scenarios)
        output_path = os.path.join(dir_scenarios, f'dose_scenario_{str(scenario_number)}.dcm')
        accumulate_dose_from_same_phase(dose_files, model3D.midp, output_path, number_of_fractions=number_of_fractions, dose_name=f'dose {number_of_fractions}fx scenario {str(scenario_number)}')


def simulate_plan_on_continuous_sequence(plan: RTPlan, midp: CTImage, ct_folder, def_fields_folder, sequence_timings, output_dose_path=None, save_all_doses=False, remove_interpolated_files=False, workdir_simu=None, downsample=0, start_irradiation=0.):
    if len(plan.spotTimings)==0:
        print('plan has no delivery timings. Querying ScanAlgo...')
        bdt = BDT(plan)
        plan = bdt.getPBSTimings(sort_spots="true")
    
    if output_dose_path is None:
        output_dose_path = os.path.join(ProgramSettings().simulationFolder, 'plan_delivery_simulations')
        if not os.path.exists(output_dose_path): os.mkdir(output_dose_path)
        output_dose_path = os.path.join(output_dose_path, 'continuous_seq')
        if not os.path.exists(output_dose_path): os.mkdir(output_dose_path)
    
    t_start = time.time()
    ctList = sorted(os.listdir(ct_folder))
    ctList = [x for x in ctList if not x.endswith('.raw') and not x.endswith('.RAW')]
    defList = sorted(os.listdir(def_fields_folder))
    defList = [x for x in defList if not x.endswith('.raw') and not x.endswith('.RAW')]

    # remove interpolated files
    if remove_interpolated_files:
        r1 = re.compile(r"_0\.[0-9]\.mhd$") # math _0.[0-9].mhd
        ctList = [x for x in ctList if r1.search(x) is None]
        defList = [x for x in defList if r1.search(x) is None]

    if downsample > 1:
        ctList = ctList[::downsample]
        defList = defList[::downsample]
        sequence_timings = sequence_timings[::downsample]

    assert len(ctList) == len(defList)
    assert len(ctList) == len(sequence_timings)

    # Split plan to list of plans
    plan_sequence = split_plan_to_continuous_sequence(plan, sequence_timings, start_irradiation)
    print(f'Plans splitted on the continuous sequence: results in {len(plan_sequence)} created.')

    # Initialize reference dose on the MidP image
    dose_MidP = DoseImage().createEmptyDoseWithSameMetaData(midp)
    dose_MidP.name = 'Accumulated dose'

    mc2 = initialize_MCsquare_params(workdir_simu)
    for i in plan_sequence:
        print(f"Importing CT {ctList[i]}")
        phaseImage = readSingleData(os.path.join(ct_folder, ctList[i]))

        dose_name = f"dose_on_phase_image_{str(i)}"
        mc2.nbPrimaries = np.minimum(1e5 * plan_sequence[i].numberOfSpots, 1e7)
        dose = mc2.computeDose(phaseImage, plan_sequence[i])
        dose.name = dose_name

        if save_all_doses:
            writeRTDose(dose, os.path.join(output_dose_path, dose_name+'.dcm'))

        ## Accumulate dose on MidP
        # Load deformation field on 3D image
        print(f"Importing deformation field {defList[i]}")
        df = readSingleData(os.path.join(def_fields_folder, defList[i]))
        df2 = Deformation3D()
        df2.initFromVelocityField(df)

        # Apply deformation field and accumulate on MidP
        dose_MidP._imageArray += df2.deformImage(dose)._imageArray


    t_end = time.time()
    print(f"it took {t_end-t_start} to simulate on the continuous sequence.")
    writeRTDose(dose_MidP, os.path.join(output_dose_path, "dose_midP_continuous_seq.dcm"))
    print("Total irradiation time:",get_irradiation_time(plan),"seconds")
    with open(os.path.join(output_dose_path, "treatment_info.txt"), 'w') as f:
        f.write(f"Total treatment time: {get_irradiation_time(plan)} seconds")


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


def split_plan_to_continuous_sequence(ReferencePlan: RTPlan, sequence_timings, start_irradiation=0.):
    # Check if plan include spot timings
    # start_irradiation \in [0,1] : moment at which to start the irradiation with beggining of 
    # continuous seq = 0. and end = 1.
    if len(ReferencePlan.spotTimings)==0:
        print('plan has no delivery timings. Querying ScanAlgo...')
        bdt = BDT(ReferencePlan)
        ReferencePlan = bdt.getPBSTimings(sort_spots="true")

    # Iterate on spots from referencePlan and add each spot to a specific image of the continuous sequence:
    plan_sequence = {} # list of plans of the sequence
    start_time = start_irradiation * sequence_timings[-1]
    beam_fraction_time = (1 / len(ReferencePlan.beams)) * sequence_timings[-1] # each beam must be started independently
    count_beam = 0
    for beam in ReferencePlan.beams:
        beam_time = count_beam * beam_fraction_time
        count_beam += 1
        for layer in beam.layers:
            for t in range(len(layer.spotTimings)):
                # Check closest sequence timing to spot timing
                current_time = (start_time + beam_time + layer.spotTimings[t]) % sequence_timings[-1] # modulo operation to restart at beggining in a loop if spotTiming > sequence_timings[-1]
                idx = np.nanargmin(np.abs(sequence_timings - current_time))
                if idx not in plan_sequence:
                    # Create plan on image idx
                    plan_sequence[idx] = ReferencePlan.createEmptyPlanWithSameMetaData()

                plan_sequence[idx].appendSpot(beam, layer, t)
    return plan_sequence



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

        # plan
        if type(plans) is dict:
            current_plan = plans[plan_names[p]]

        # Create MCsquare simulation
        mc2 = initialize_MCsquare_params()
        if crop_contour is not None:
            mc2.overwriteOutsideROI = crop_contour
        dose = mc2.computeDose(CT, current_plan)
        writeRTDose(dose, os.path.join(output_path, f"{dose_prefix}{p:03d}.dcm"))


def initialize_MCsquare_params(workdir=None):
    mc2 = MCsquareDoseCalculator()
    if workdir is not None:
      mc2.simulationDirectory = workdir

    mc2.ctCalibration = readScanner(DoseCalculationConfig().scannerFolder)
    mc2.beamModel = mcsquareIO.readBDL(DoseCalculationConfig().bdlFile)
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


def get_irradiation_time(plan):
    assert len(plan.spotTimings)>0
    total_time = [plan.beams[i].layers[-1].spotTimings[-1] for i in range(len(plan.beams))]
    return np.sum(total_time)
