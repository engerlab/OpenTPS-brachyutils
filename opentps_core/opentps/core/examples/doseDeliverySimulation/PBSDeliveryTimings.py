import sys
sys.path.append('..')

from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.processing.planDeliverySimulation.beamDeliveryTimings import BDT
from opentps.core.io.dicomIO import readDicomPlan

"""
#### Config file: text file openTPS_workspace/config/DeliverySimulationConfig with 2 lines
that need to be filled with ScanAlgo parameters:
gantry = <TYPE OF GANTRY>
gateway = <URL>
"""

# load OpenTPS plan
plan_path = r"C:\Users\valentin.hamaide\data\ARIES\patient_0\plan_4D_robust.dcm"
plan = readDicomPlan(plan_path)

#### Conventional PT usage.Gantry
# Add PBS timings into a plan
bdt = BDT(plan)
plan_with_timings = bdt.getPBSTimings(sort_spots="true")

# print plan
print(plan_with_timings._beams[0]._layers[0].__dict__)
