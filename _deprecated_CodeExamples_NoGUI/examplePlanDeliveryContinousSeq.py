import numpy as np
from opentps.core.io.dataLoader import readData
from opentps.core.io.dicomIO import readDicomPlan
from opentps.core.data.images._ctImage import CTImage
from opentps.core.processing.planDeliverySimulation.planDeliverySimulation import simulate_plan_on_continuous_sequence


def get_sequence_timings_from_txt_file(sequence_timings_filepath, return_tracker_amplitude=False):
    data = np.loadtxt(sequence_timings_filepath, delimiter=' ', skiprows=4, usecols=(0,1))
    sequence_timings = data[:,0]
    sequence_timings -= sequence_timings[0] # start at 0
    sequence_timings /= 1000 # transform ms to seconds
    tracker_amplitude = data[:,1]
    if return_tracker_amplitude: return sequence_timings, tracker_amplitude
    return sequence_timings


######## Simulation on 4DCT #########
patient_name = 'patient_0'

# Load plan
plan_path = f'/data/vhamaide/liver/{patient_name}/MidP_CT/Raystation/plan_4D_robust.dcm'
plan = readDicomPlan(plan_path)
plan.numberOfFractionsPlanned = 30

# Load 4DCT
ct_folder = f'/data/vhamaide/liver/{patient_name}/deformed_phases_cropped_body/'

# Load MidP
MidPCT_Path = f'/data/vhamaide/liver/{patient_name}/MidP_CT_croppedXY/'
midP = readData(MidPCT_Path, 0)
midP = [data for data in midP if type(data) is CTImage][0]

# Load deformation fields
def_fields_folder = f"/data/vhamaide/liver/{patient_name}/VelocityFieldsByFrame_MHD/"

sequence_timings_filepath = f'/data/vhamaide/liver/{patient_name}/MRI_Pos1Cor_CropToCT_Multi_5_r.txt'
sequence_timings = get_sequence_timings_from_txt_file(sequence_timings_filepath)

simulate_plan_on_continuous_sequence(plan, midP, ct_folder, def_fields_folder, sequence_timings, output_dose_path=None, save_all_doses=True, remove_interpolated_files=True, workdir_simu=None, downsample=4, start_irradiation=0.)