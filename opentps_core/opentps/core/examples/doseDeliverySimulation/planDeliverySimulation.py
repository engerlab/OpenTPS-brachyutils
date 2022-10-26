import matplotlib.pyplot as plt

from opentps.core.io.dataLoader import readData
from opentps.core.io.dicomIO import readDicomPlan
from opentps.core.data.images._ctImage import CTImage
from opentps.core.data.images._deformation3D import Deformation3D
from opentps.core.data._rtStruct import RTStruct
from opentps.core.processing.planDeliverySimulation.planDeliverySimulation import *

######## Simulation on 4DCT #########
patient_name = 'patient_0'

# Load plan
plan_path = r"C:\Users\valentin.hamaide\data\ARIES\patient_0\plan_4D_robust.dcm"
plan = readDicomPlan(plan_path)

# Load 4DCT
dataPath = r"C:\Users\valentin.hamaide\data\ARIES\patient_0\4DCT"
dataList = readData(dataPath, 1)
CT4D = [data for data in dataList if type(data) is CTImage]
CT4D = Dynamic3DSequence(CT4D)

# Load model3D
MidPCT_Path = r"C:\Users\valentin.hamaide\data\ARIES\patient_0\MidP_CT"
midP_data = readData(MidPCT_Path, 0)
midP = [data for data in midP_data if type(data) is CTImage][0]
# Load MidP RT struct
midP_struct = [data for data in midP_data if type(data) is RTStruct][0]

# Load deformation fields
inputPaths = r"C:\Users\valentin.hamaide\data\ARIES\patient_0\deformation_fields"
defList = readData(inputPaths, 0)

# Transform VectorField3D to deformation3D
deformationList = []
for df in defList:
    df2 = Deformation3D()
    df2.initFromVelocityField(df)
    deformationList.append(df2)
del defList
print(deformationList)

# Create Dynamic 3D Model
model3D = Dynamic3DModel(name=patient_name, midp=midP, deformationList=deformationList)
print(model3D)

PDS = PlanDeliverySimulation(plan, CT4D, model3D)

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