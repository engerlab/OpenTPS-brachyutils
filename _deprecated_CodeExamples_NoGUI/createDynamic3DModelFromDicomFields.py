import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
from opentps_core.opentps.core.IO import readData
from opentps_core.opentps.core.data.Images._deformation3D import Deformation3D
from opentps_core.opentps.core.data import Dynamic3DModel

# Load DICOM CT
patient_name = 'Patient_1'
inputPaths = f"/data/public/liver/{patient_name}/MidP_ct/"
dataList = readData(inputPaths, maxDepth=0)
midP = dataList[0]
print(type(midP))

# Load DICOM Deformation Fields
inputPaths = f"/data/public/liver/{patient_name}/deformation_fields/"
defList = readData(inputPaths, maxDepth=0)

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