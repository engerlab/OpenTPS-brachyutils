import os
import sys

from opentps.core.io.dataLoader import readData
from opentps.core.data.images._deformation3D import Deformation3D
from opentps.core.data.dynamicData._dynamic3DModel import Dynamic3DModel

# Load DICOM CT
inputPaths = f"/data/MidP_ct/"
dataList = readData(inputPaths, maxDepth=0)
midP = dataList[0]
print(type(midP))

# Load DICOM Deformation Fields
inputPaths = f"/data/deformation_fields/"
defList = readData(inputPaths, maxDepth=0)

# Transform VectorField3D to deformation3D
deformationList = []
for df in defList:
    df2 = Deformation3D()
    df2.initFromVelocityField(df)
    deformationList.append(df2)
del defList
print(deformationList)

patient_name = 'OpenTPS_Patient'

# Create Dynamic 3D Model
model3D = Dynamic3DModel(name=patient_name, midp=midP, deformationList=deformationList)
print(model3D)