import matplotlib.pyplot as plt

from opentps.core.io.dataLoader import readData
from opentps.core.io.dicomIO import readDicomPlan, readDicomStruct
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._deformation3D import Deformation3D
from opentps.core.data._rtStruct import RTStruct
from opentps.core.processing.planDeliverySimulation.planDeliverySimulation import *

######## Simulation on 4DCT #########

# Load plan
plan_path = "path/to/dicom/plan"
plan = readDicomPlan(plan_path)

# Load 4DCT
dataPath = "path/to/4DCT_folder"
dataList = readData(dataPath, 1)
CT4D = [data for data in dataList if type(data) is CTImage]
CT4D = Dynamic3DSequence(CT4D)

# If already have a 3D model, load it and pass it to PlanDeliverySimulation:
# model3D = pickle.load('path/to_model3D')

# Create plan delivery object
PDS = PlanDeliverySimulation(plan, CT4D)

## 4D Dose simulation
PDS.simulate4DDose()

## 4D dynamic simulation
PDS.simulate4DDynamicDose()

## Simulate fractionation scenarios
number_of_fractions=5 # number of fractions of the plan
number_of_starting_phases=3 # number of simulations (from a different starting phase)
number_of_fractionation_scenarios=7 # how many scenarios we select where each scenario is a random combination with replacement
PDS.simulate4DDynamicDoseScenarios(number_of_fractions=number_of_fractions, number_of_starting_phases=number_of_starting_phases, number_of_fractionation_scenarios=number_of_fractionation_scenarios)

# # Plot DVH with bands for a single fraction
midP_struct_path = 'path/to/dicom_struct'
midP_struct = readDicomStruct(midP_struct_path)
dvh_bands = PDS.computeDVHBand4DDD(midP_struct.contours, singleFraction=True)

# # Display DVH + DVH-bands
fig, ax = plt.subplots(1, 1, figsize=(5, 5))
for dvh_band in dvh_bands:
    phigh = ax.plot(dvh_band._dose, dvh_band._volumeHigh, alpha=0)
    plow = ax.plot(dvh_band._dose, dvh_band._volumeLow, alpha=0)
    pNominal = ax.plot(dvh_band._nominalDVH._dose, dvh_band._nominalDVH._volume, label=dvh_band._roiName)
    pfill = ax.fill_between(dvh_band._dose, dvh_band._volumeHigh, dvh_band._volumeLow, alpha=0.2)
ax.set_xlabel("Dose (Gy)")
ax.set_ylabel("Volume (%)")
plt.grid(True)
plt.legend()
plt.show()


# Plot DVH with band for the accumulation of 5 fractions
dvh_bands = PDS.computeDVHBand4DDD(midP_struct.contours, singleFraction=False)

# Display DVH + DVH-bands
fig, ax = plt.subplots(1, 1, figsize=(5, 5))
for dvh_band in dvh_bands:
    phigh = ax.plot(dvh_band._dose, dvh_band._volumeHigh, alpha=0)
    plow = ax.plot(dvh_band._dose, dvh_band._volumeLow, alpha=0)
    pNominal = ax.plot(dvh_band._nominalDVH._dose, dvh_band._nominalDVH._volume, label=dvh_band._roiName)
    pfill = ax.fill_between(dvh_band._dose, dvh_band._volumeHigh, dvh_band._volumeLow, alpha=0.2)
ax.set_xlabel("Dose (Gy)")
ax.set_ylabel("Volume (%)")
plt.grid(True)
plt.legend()
plt.show()