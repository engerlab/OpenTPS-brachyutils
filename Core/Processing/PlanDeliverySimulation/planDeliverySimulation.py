from typing import Optional, Sequence, Union
import opentps
import os
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

    fx_dir = os.path.join(simulation_dir, f'{plan.numberOfFractionsPlanned}_fx')
    dir_4DD = os.path.join(fx_dir, '4DD')
    if not os.path.exists(fx_dir):
        os.mkdir(fx_dir)
    if not os.path.exists(dir_4DD):
        os.mkdir(dir_4DD)

    compute_dose_on_each_phase(plan, CT4D, dir_4DD, crop_contour=crop_contour)
    output_accumulated_dose = os.path.join(dir_4DD, "dose_accumulated_4DD.dcm")
    accumulate_dose_reference_phase(dir_4DD, model3D, output_accumulated_dose, divide_total_dose=True, dose_name='4DD Accumulated dose')


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


def accumulate_dose_reference_phase(dose_4DCT_path:str, model3D: Dynamic3DModel, output_path:str, divide_total_dose=False, dose_name='Accumulated dose'):
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
