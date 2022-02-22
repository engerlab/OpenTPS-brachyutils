import os
import unittest

import numpy as np

from Core.Data.Images.ctImage import CTImage
from Core.Data.MCsquare.bdl import BDL
from Core.Data.Plan.rangeShifter import RangeShifter
from Core.Data.Plan.rtPlan import RTPlan


def readBDL(path) -> BDL:
    bdl = BDL()

    with open(path, 'r') as fid:
        # verify BDL format
        line = fid.readline()
        fid.seek(0)
        if not "--UPenn beam model (double gaussian)--" in line and not "--Lookup table BDL format--" in line:
            fid.close()
            raise IOError("BDL format not supported")

        line_num = -1
        readNIDist = False
        smx = False
        smy = False
        for line in fid:
            line_num += 1

            # remove comments
            if line[0] == '#': continue
            line = line.split('#')[0]

            if "Nozzle exit to Isocenter distance" in line:
                readNIDist = True
                continue
            if readNIDist:
                line = line.split()
                bdl.nozzle_isocenter = float(line[0])
                readNIDist = False
                continue

            if "SMX" in line:
                smx = True
                continue
            if smx:
                line = line.split()
                bdl.smx = float(line[0])
                smx = False
                continue

            if "SMY" in line:
                smy = True
                continue
            if smy:
                line = line.split()
                bdl.smy = float(line[0])
                smy = False
                continue

            # find begining of the BDL table in the file
            if ("NominalEnergy" in line): table_line = line_num + 1

            # parse range shifter data
            if ("Range Shifter parameters" in line):
                RS = RangeShifter()
                bdl.RangeShifters.append(RS)

            if ("RS_ID" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.RangeShifters[-1].ID = value

            if ("RS_type" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.RangeShifters[-1].type = value.lower()

            if ("RS_material" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.RangeShifters[-1].material = int(value)

            if ("RS_density" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.RangeShifters[-1].density = float(value)

            if ("RS_WET" in line):
                line = line.split('=')
                value = line[1].replace('\r', '').replace('\n', '').replace('\t', '').replace(' ', '')
                bdl.RangeShifters[-1].WET = float(value)

    # parse BDL table
    BDL_table = np.loadtxt(path, skiprows=table_line)

    bdl.NominalEnergy = BDL_table[:, 0]
    bdl.MeanEnergy = BDL_table[:, 1]
    bdl.EnergySpread = BDL_table[:, 2]
    bdl.ProtonsMU = BDL_table[:, 3]
    bdl.Weight1 = BDL_table[:, 4]
    bdl.SpotSize1x = BDL_table[:, 5]
    bdl.Divergence1x = BDL_table[:, 6]
    bdl.Correlation1x = BDL_table[:, 7]
    bdl.SpotSize1y = BDL_table[:, 8]
    bdl.Divergence1y = BDL_table[:, 9]
    bdl.Correlation1y = BDL_table[:, 10]
    bdl.Weight2 = BDL_table[:, 11]
    bdl.SpotSize2x = BDL_table[:, 12]
    bdl.Divergence2x = BDL_table[:, 13]
    bdl.Correlation2x = BDL_table[:, 14]
    bdl.SpotSize2y = BDL_table[:, 15]
    bdl.Divergence2y = BDL_table[:, 16]
    bdl.Correlation2y = BDL_table[:, 17]

    return bdl


def writeBDL(bdl: BDL, fileName):
    with open(fileName, 'w') as f:
        f.write(bdl.mcsquareFormatted())


def writePlan(plan: RTPlan, file_path, CT:CTImage, bdl:BDL):
    DestFolder, DestFile = os.path.split(file_path)
    FileName, FileExtension = os.path.splitext(DestFile)

    # export plan
    print("Write Plan: " + file_path + ' in ' + DestFolder)
    fid = open(file_path, 'w')
    fid.write("#TREATMENT-PLAN-DESCRIPTION\n")
    fid.write("#PlanName\n")
    fid.write("%s\n" % FileName)
    fid.write("#NumberOfFractions\n")
    fid.write("%d\n" % plan.numberOfFractionsPlanned)
    fid.write("##FractionID\n")
    fid.write("1\n")
    fid.write("##NumberOfFields\n")
    fid.write("%d\n" % len(plan))
    for i in range(len(plan)):
        fid.write("###FieldsID\n")
        fid.write("%d\n" % (i + 1))
    fid.write("#TotalMetersetWeightOfAllFields\n")
    fid.write("%f\n" % plan.meterset)

    for i, beam in enumerate(plan):
        fid.write("\n")
        fid.write("#FIELD-DESCRIPTION\n")
        fid.write("###FieldID\n")
        fid.write("%d\n" % (i + 1))
        fid.write("###FinalCumulativeMeterSetWeight\n")
        fid.write("%f\n" % beam.meterset)
        fid.write("###GantryAngle\n")
        fid.write("%f\n" % beam.gantryAngle)
        fid.write("###PatientSupportAngle\n")
        fid.write("%f\n" % beam.patientSupportAngle)
        fid.write("###IsocenterPosition\n")
        fid.write("%f\t %f\t %f\n" % _dicomIsocenterToMCsquare(beam.isocenterPosition, CT.origin, CT.spacing, CT.gridSize))

        if not(beam.rangeShifter is None):
            if not (beam.rangeShifter in bdl.RangeShifters):
                raise Exception('Range shifter in plan not in BDL')
            else:
                fid.write("###RangeShifterID\n")
                fid.write("%s\n" % beam.rangeShifter.ID)
                fid.write("###RangeShifterType\n")
                fid.write("binary\n")

        fid.write("###NumberOfControlPoints\n")
        fid.write("%d\n" % len(beam))
        fid.write("\n")
        fid.write("#SPOTS-DESCRIPTION\n")

        for j, layer in enumerate(beam):
            fid.write("####ControlPointIndex\n")
            fid.write("%d\n" % (j + 1))
            fid.write("####SpotTunnedID\n")
            fid.write("1\n")
            fid.write("####CumulativeMetersetWeight\n")
            fid.write("%f\n" % layer.meterset)
            fid.write("####Energy (MeV)\n")
            fid.write("%f\n" % layer.nominalEnergy)

            if not(beam.rangeShifter is None) and (beam.rangeShifter.type == "binary"):
                fid.write("####RangeShifterSetting\n")
                fid.write("%s\n" % layer.rangeShifterSettings.rangeShifterSetting)
                fid.write("####IsocenterToRangeShifterDistance\n")
                fid.write("%f\n" % layer.rangeShifterSettings.isocenterToRangeShifterDistance)
                fid.write("####RangeShifterWaterEquivalentThickness\n")
                if (layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness is None):
                    fid.write("%f\n" % beam.rangeShifter.WET)
                else:
                    fid.write("%f\n" % layer.rangeShifterSettings.rangeShifterWaterEquivalentThickness)

            fid.write("####NbOfScannedSpots\n")
            fid.write("%d\n" % len(layer))

            fid.write("####X Y Weight\n")
            for i, xy in enumerate(layer.spotXY):
                fid.write("%f %f %f\n" % (xy[0], xy[1], layer.spotWeights[i]))

    fid.close()

def _dicomIsocenterToMCsquare(isocenter, ctImagePositionPatient, ctPixelSpacing, ctGridSize):
    MCsquareIsocenter0 = isocenter[0] - ctImagePositionPatient[0] + ctPixelSpacing[0] / 2  # change coordinates (origin is now in the corner of the image)
    MCsquareIsocenter1 = isocenter[1] - ctImagePositionPatient[1] + ctPixelSpacing[1] / 2
    MCsquareIsocenter2 = isocenter[2] - ctImagePositionPatient[2] + ctPixelSpacing[2] / 2

    MCsquareIsocenter1 = ctGridSize[1] * ctPixelSpacing[1] - MCsquareIsocenter1  # flip coordinates in Y direction

    return (MCsquareIsocenter0, MCsquareIsocenter1, MCsquareIsocenter2)

def _deliveredProtons(plan:RTPlan, bdl:BDL) -> tuple:
    deliveredProtons = 0
    beamletRescaling = []
    for beam in plan:
        for layer in beam:
            Protons_per_MU = bdl.computeMU2Protons(layer.nominalEnergy)
            deliveredProtons += sum(layer.spotWeights) * Protons_per_MU
            for i in range(len(layer)):
                beamletRescaling.append(Protons_per_MU * 1.602176e-19 * 1000)

    return (deliveredProtons, beamletRescaling)


class MCsquareIOTestCase(unittest.TestCase):
    def testWrite(self):
        from Core.Data.Plan.planIonBeam import PlanIonBeam
        from Core.Data.Plan.planIonLayer import PlanIonLayer

        import MCsquare.BDL as BDLModule

        bdl = readBDL(os.path.join(str(BDLModule.__path__[0]), 'BDL_default_DN_RangeShifter.txt'))

        plan = RTPlan()
        beam = PlanIonBeam()
        layer = PlanIonLayer(nominalEnergy=100.)
        layer.appendSpot(0, 0, 1)
        layer.appendSpot(0, 1, 2)

        beam.appendLayer(layer)

        plan.appendBeam(beam)

        writePlan(plan, 'plan_test.txt', CTImage(), bdl)
