import os
from opentps_core.opentps.core.IO import readData, mcsquareIO
from opentps_core.opentps.core.Processing.DoseCalculation import MCsquareDoseCalculator
from opentps_core.opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareCTCalibration import MCsquareCTCalibration
from opentps_core.opentps.core.data.Plan._planDesign import PlanDesign
from opentps_core.opentps.core.IO import saveRTPlan, saveBeamlets

# CT path
ctImagePath = "/home/sophie/Documents/Protontherapy/OpenTPS/arc_dev/opentps_core/data/Plan_IMPT_patient1"
# Output path
output_path = os.path.join(ctImagePath, "OpenTPS")

# Create output folder
if not os.path.isdir(output_path):
    os.mkdir(output_path)

# Load patient data
dataList = readData(ctImagePath, maxDepth=0)
ct = dataList[7]
contours = dataList[6]
print('Available ROIs')
contours.print_ROINames()

# Configure MCsquare
MCSquarePath = '../core/Processing/DoseCalculation/MCsquare/'
mc2 = MCsquareDoseCalculator()
beamModel = mcsquareIO.readBDL(os.path.join(MCSquarePath, 'BDL', 'UMCG_P1_v2_RangeShifter.txt'))
mc2.beamModel = beamModel
# small number of primaries for beamlet calculation
mc2.nbPrimaries = 5e4
# Downsample resolution for large CT
mc2.independentScoringGrid = True
mc2.scoringVoxelSpacing = [5.0, 5.0, 5.0]

scannerPath = os.path.join(MCSquarePath, 'Scanners', 'UCL_Toshiba')
calibration = MCsquareCTCalibration(fromFiles=(os.path.join(scannerPath, 'HU_Density_Conversion.txt'),
                                               os.path.join(scannerPath, 'HU_Material_Conversion.txt'),
                                               os.path.join(MCSquarePath, 'Materials')))
mc2.ctCalibration = calibration

# ROIs
target = contours.getContourByName('CTV')
targetMask = target.getBinaryMask(origin=ct.origin, gridSize=ct.gridSize, spacing=ct.spacing)
opticChiasm = contours.getContourByName('Optic Chiasm')
brainStem = contours.getContourByName('Brain Stem')
body = contours.getContourByName('BODY')

L = []
for i in range(len(contours)):
    L.append(contours[i].name)

#ROI = [body.name]
ROI = [target.name]

# Crop Beamlets on ROI to save computation time ! not mandatory
ROIforBL = []
for i in range(len(ROI)):
    index_value = L.index(ROI[i])
    # add contour
    ROIforBL.append(contours[index_value])


# Beam configuration
beamNames = ["Beam1", "Beam2"]
gantryAngles = [100., 280.]
couchAngles = [0., 0.]

# Generate new plan
plan_file = os.path.join(output_path, "brain_100_280.tps")
planInit = PlanDesign()
planInit.ct = ct
planInit.targetMask = targetMask
planInit.gantryAngles = gantryAngles
planInit.beamNames = beamNames
planInit.couchAngles = couchAngles
planInit.calibration = calibration
planInit.spotSpacing = 6.0
planInit.layerSpacing = 4.0
planInit.targetMargin = 6.0
plan = planInit.createPlan()  # Spot placement
plan.PlanName = "NewPlan"
saveRTPlan(plan, plan_file)

# Beamlet calculation
# last argument is optional (used to crop BL)
beamlets = mc2.computeBeamlets(ct, plan, ROIforBL)
outputBeamletFile = os.path.join(output_path, "BeamletMatrix_" + plan.seriesInstanceUID + ".blm")
saveBeamlets(beamlets, outputBeamletFile)
