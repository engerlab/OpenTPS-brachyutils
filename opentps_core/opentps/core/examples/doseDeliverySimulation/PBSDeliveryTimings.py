import numpy as np
np.random.seed(42)
from opentps.core.data.plan._planIonBeam import PlanIonBeam
from opentps.core.data.plan._planIonLayer import PlanIonLayer
from opentps.core.data.plan._rtPlan import RTPlan
from opentps.core.processing.planDeliverySimulation.scanAlgoBeamDeliveryTimings import ScanAlgoBeamDeliveryTimings
from opentps.core.processing.planDeliverySimulation.simpleBeamDeliveryTimings import SimpleBeamDeliveryTimings
from opentps.core.io.dicomIO import readDicomPlan

# Create random plan
plan = RTPlan()
plan.appendBeam(PlanIonBeam())
energies = np.array([130, 140, 150, 160, 170])
for m in energies:
    layer = PlanIonLayer(m)
    x = 10*np.random.random(5) - 5
    y = 10*np.random.random(5) - 5
    mu = 5*np.random.random(5)

    layer.appendSpot(x, y, mu)
    plan.beams[0].appendLayer(layer)


bdt = SimpleBeamDeliveryTimings(plan)
plan_with_timings = bdt.getPBSTimings(sort_spots="true")

# print plan
print(plan_with_timings._beams[0]._layers[0].__dict__)
