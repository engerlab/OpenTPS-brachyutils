import os
import sys
currentWorkingDir = os.getcwd()
while not os.path.isfile(currentWorkingDir + '/main.py'): currentWorkingDir = os.path.dirname(currentWorkingDir)
sys.path.append(currentWorkingDir)
from Core.IO.dataLoader import loadAllData
from Core.Data.Images.deformation3D import Deformation3D
from Core.Data.DynamicData.dynamic3DModel import Dynamic3DModel

# Load DICOM CT
patient_name = 'Patient_1'
inputPaths = f"/data/public/liver/{patient_name}/MidP_ct/"
dataList = loadAllData(inputPaths, maxDepth=0)
midP = dataList[0]
print(type(midP))

# Load DICOM Deformation Fields
inputPaths = f"/data/public/liver/{patient_name}/deformation_fields/"
defList = loadAllData(inputPaths, maxDepth=0)

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