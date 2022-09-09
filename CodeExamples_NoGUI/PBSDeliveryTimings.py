import sys
sys.path.append('..')

from Core.Data.Plan._rtPlan import RTPlan
from Core.Data.Plan._beamDeliveryTimings import BDT
from Core.IO.dicomIO import readDicomPlan


# load OpenTPS plan
plan_path = '/data/vhamaide/liver/patient_0/MidP_CT/Raystation/plan_4D_robust.dcm'
plan = readDicomPlan(plan_path)

#### Conventional PT usage.Gantry
# Add PBS timings into a plan
congig_path = '../config/config_scanAlgo.txt'
bdt = BDT(plan, congig_path)
plan_with_timings = bdt.getPBSTimings(sort_spots="true")

# print plan
print(plan_with_timings._beams[0]._layers[0].__dict__)