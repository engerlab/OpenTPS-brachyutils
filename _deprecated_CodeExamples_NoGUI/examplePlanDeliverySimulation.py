import sys
sys.path.append('..')
from opentps_core.opentps.core.IO import readData
from opentps_core.opentps.core.IO import readDicomPlan
from opentps_core.opentps.core.data import CTImage
from opentps_core.opentps.core.data.Images._deformation3D import Deformation3D

######## Simulation on 4DCT #########
patient_name = 'patient_0'

# Load plan
plan_path = f'/data/vhamaide/liver/{patient_name}/MidP_CT/Raystation/plan_4D_robust.dcm'
plan = readDicomPlan(plan_path)

# Load 4DCT
dataPath = f'/data/vhamaide/liver/{patient_name}/4DCT'
dataList = readData(dataPath, 1)
CT4D = [data for data in dataList if type(data) is CTImage]
CT4D = Dynamic3DSequence(CT4D)

# Load model3D
MidPCT_Path = f'/data/vhamaide/liver/{patient_name}/MidP_CT/'
midP = readData(MidPCT_Path, 0)
midP = [data for data in midP if type(data) is CTImage][0]

# Load deformation fields
inputPaths = f"/data/vhamaide/liver/{patient_name}/deformation_fields/"
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


### 4D Dose simulation
simulate_4DD(plan, CT4D, model3D)

## 4D dynamic simulation
simulate_4DDD(plan, CT4D, model3D)

## Simulate fractionation scenarios
simulate_4DDD_scenarios(plan, CT4D, model3D, number_of_fractions=5, number_of_starting_phases=3, number_of_fractionation_scenarios=5)