import copy
import logging
import pickle
import statistics
import time

import pydicom
from Core.Data.SPRimage import *
from Core.Data.patientData import PatientData
from Core.Processing.OptimizationObjectives import *
from Core.Processing.C_libraries.libRayTracing_wrapper import *

logger = logging.getLogger(__name__)


class RTplan(PatientData):

    def __init__(self, patientInfo=None):
        super().__init__(patientInfo=patientInfo):
        self.deliveredProtons = None
        self.seriesInstanceUID = ""
        self.sopInstanceUID = ""
        self.studyInfo = {}
        self.dcmFile = ""
        self.modality = ""
        self.radiationType = ""
        self.scanMode = ""
        self.treatmentMachineName = ""
        self.numberOfFractionsPlanned = 1
        self.numberOfSpots = 0
        self.beams = []
        self.totalMeterset = 0.0
        self.planName = ""
        self.objectives = OptimizationObjectives()
        self.isLoaded = 0
        self.beamlets = []
        self.originalDicomDataset = []
        self.robustOpti = {"Strategy": "Disabled", "syst_setup": [0.0, 0.0, 0.0], "rand_setup": [0.0, 0.0, 0.0],
                           "syst_range": 0.0}
        self.scenarios = []
        self.numScenarios = 0

    def printPlanInfo(self, prefix=""):
        logger.info(prefix + "Plan: " + self.seriesInstanceUID)
        logger.info(prefix + "   " + self.dcmFile)

    def printPlanStat(self):
        logger.info("Number of fractions: {}".format(self.numberOfFractionsPlanned))
        logger.info("Number of beams: {}".format(len(self.beams)))
        logger.info("Number of spots: {}".format(self.numberOfSpots))

        for beam in self.beams:
            logger.info(" ")
            logger.info("Beam: Gantry %.1f°, Couch %.1f°" % (beam.gantryAngle, beam.patientSupportAngle))
            for layer in beam.layers:
                if len(layer.spotMU) == 1:
                    logger.info("  Layer %3.1f MeV: %2d spots, %2.2f +/- %2.2f MU/spot" % (
                        layer.nominalBeamEnergy, len(layer.spotMU), layer.spotMU[0], 0.0))
                else:
                    logger.info("  Layer %3.1f MeV: %2d spots, %2.2f +/- %2.2f MU/spot" % (
                        layer.nominalBeamEnergy, len(layer.spotMU), statistics.mean(layer.spotMU),
                        statistics.stdev(layer.spotMU)))

    def importDicomPlan(self):
        if self.isLoaded == 1:
            logger.warning("RTplan " + self.seriesInstanceUID + " is already loaded")
            return

        dcm = pydicom.dcmread(self.dcmFile)

        self.originalDicomDataset = dcm

        # Photon plan
        if dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.5":
            logger.error("Conventional radiotherapy (photon) plans are not supported")
            self.modality = "Radiotherapy"
            return

        # Ion plan
        elif dcm.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.8":
            self.modality = "Ion therapy"

            if dcm.IonBeamSequence[0].RadiationType == "PROTON":
                self.radiationType = "Proton"
            else:
                logger.error("Radiation type " + dcm.IonBeamSequence[0].RadiationType + " not supported")
                self.radiationType = dcm.IonBeamSequence[0].RadiationType
                return

            if dcm.IonBeamSequence[0].scanMode == "MODULATED":
                self.scanMode = "MODULATED"  # PBS
            elif dcm.IonBeamSequence[0].scanMode == "LINE":
                self.scanMode = "LINE"  # Line Scanning
            else:
                logger.error("Scan mode " + dcm.IonBeamSequence[0].scanMode + " not supported")
                self.scanMode = dcm.IonBeamSequence[0].scanMode
                return

                # Other
        else:
            logger.error("Unknown SOPClassUID " + dcm.SOPClassUID + " for file " + self.dcmFile)
            self.modality = "Unknown"
            return

        # Start parsing PBS plan
        self.sopInstanceUID = dcm.SOPInstanceUID
        self.numberOfFractionsPlanned = int(dcm.FractionGroupSequence[0].NumberOfFractionsPlanned)
        self.numberOfSpots = 0
        self.totalMeterset = 0

        if hasattr(dcm.IonBeamSequence[0], 'TreatmentMachineName'):
            self.treatmentMachineName = dcm.IonBeamSequence[0].TreatmentMachineName
        else:
            self.treatmentMachineName = ""

        for dcm_beam in dcm.IonBeamSequence:
            if dcm_beam.TreatmentDeliveryType != "TREATMENT":
                continue

            firstLayer = dcm_beam.IonControlPointSequence[0]

            beam = PlanIonBeam()
            beam.seriesInstanceUID = self.seriesInstanceUID
            beam.beamName = dcm_beam.beamName
            beam.isocenterPosition = [float(firstLayer.isocenterPosition[0]), float(firstLayer.isocenterPosition[1]),
                                      float(firstLayer.isocenterPosition[2])]
            beam.gantryAngle = float(firstLayer.gantryAngle)
            beam.patientSupportAngle = float(firstLayer.patientSupportAngle)
            beam.finalCumulativeMetersetWeight = float(dcm_beam.finalCumulativeMetersetWeight)

            # find corresponding beam in FractionGroupSequence (beam order may be different from IonBeamSequence)
            referencedBeamId = next((x for x, val in enumerate(dcm.FractionGroupSequence[0].ReferencedBeamSequence) if
                                     val.ReferencedBeamNumber == dcm_beam.BeamNumber), -1)
            if referencedBeamId == -1:
                logger.error("Beam number " + dcm_beam.BeamNumber + " not found in FractionGroupSequence.")
                logger.info("This beam is therefore discarded.")
                continue
            else:
                beam.beamMeterset = float(
                    dcm.FractionGroupSequence[0].ReferencedBeamSequence[referencedBeamId].beamMeterset)

            self.totalMeterset += beam.beamMeterset

            if dcm_beam.NumberOfRangeShifters == 0:
                beam.rangeShifterID = ""
                beam.rangeShifterType = "none"
            elif dcm_beam.NumberOfRangeShifters == 1:
                beam.rangeShifterID = dcm_beam.RangeShifterSequence[0].rangeShifterID
                if dcm_beam.RangeShifterSequence[0].RangeShifterType == "BINARY":
                    beam.rangeShifterType = "binary"
                elif dcm_beam.RangeShifterSequence[0].RangeShifterType == "ANALOG":
                    beam.rangeShifterType = "analog"
                else:
                    logger.error("Unknown range shifter type for beam " + dcm_beam.beamName)
                    beam.rangeShifterType = "none"
            else:
                logger.error("More than one range shifter defined for beam " + dcm_beam.beamName)
                beam.rangeShifterID = ""
                beam.rangeShifterType = "none"

            snoutPosition = 0
            if hasattr(firstLayer, 'SnoutPosition'):
                snoutPosition = float(firstLayer.SnoutPosition)

            isocenterToRangeShifterDistance = snoutPosition
            rangeShifterWaterEquivalentThickness = ""
            rangeShifterSetting = "OUT"
            referencedRangeShifterNumber = 0

            if hasattr(firstLayer, 'RangeShifterSettingsSequence'):
                if hasattr(firstLayer.RangeShifterSettingsSequence[0], 'IsocenterToRangeShifterDistance'):
                    isocenterToRangeShifterDistance = float(
                        firstLayer.RangeShifterSettingsSequence[0].isocenterToRangeShifterDistance)
                if hasattr(firstLayer.RangeShifterSettingsSequence[0], 'RangeShifterWaterEquivalentThickness'):
                    rangeShifterWaterEquivalentThickness = float(
                        firstLayer.RangeShifterSettingsSequence[0].rangeShifterWaterEquivalentThickness)
                if hasattr(firstLayer.RangeShifterSettingsSequence[0], 'RangeShifterSetting'):
                    rangeShifterSetting = firstLayer.RangeShifterSettingsSequence[0].rangeShifterSetting
                if hasattr(firstLayer.RangeShifterSettingsSequence[0], 'ReferencedRangeShifterNumber'):
                    referencedRangeShifterNumber = int(
                        firstLayer.RangeShifterSettingsSequence[0].referencedRangeShifterNumber)

            cumulativeMeterset = 0

            for dcmLayer in dcm_beam.IonControlPointSequence:
                if self.scanMode == "MODULATED":
                    if dcmLayer.NumberOfScanSpotPositions == 1:
                        sumWeights = dcmLayer.scanSpotMetersetWeights
                    else:
                        sumWeights = sum(dcmLayer.scanSpotMetersetWeights)

                elif self.scanMode == "LINE":
                    sumWeights = sum(np.frombuffer(dcmLayer[0x300b1096].value, dtype=np.float32).tolist())

                if sumWeights == 0.0:
                    continue

                layer = PlanIonLayer()
                layer.seriesInstanceUID = self.seriesInstanceUID

                if hasattr(dcmLayer, 'SnoutPosition'):
                    snoutPosition = float(dcmLayer.SnoutPosition)

                if hasattr(dcmLayer, 'NumberOfPaintings'):
                    layer.numberOfPaintings = int(dcmLayer.numberOfPaintings)
                else:
                    layer.numberOfPaintings = 1

                layer.nominalBeamEnergy = float(dcmLayer.nominalBeamEnergy)

                if self.scanMode == "MODULATED":
                    layer.scanSpotPositionMap_x = dcmLayer.ScanSpotPositionMap[0::2]
                    layer.scanSpotPositionMap_y = dcmLayer.ScanSpotPositionMap[1::2]
                    layer.scanSpotMetersetWeights = dcmLayer.scanSpotMetersetWeights
                    # spot weights are converted to MU
                    layer.spotMU = np.array(
                        dcmLayer.scanSpotMetersetWeights) * beam.beamMeterset / beam.finalCumulativeMetersetWeight

                    if layer.spotMU.size == 1:
                        layer.spotMU = [layer.spotMU]
                    else:
                        layer.spotMU = layer.spotMU.tolist()
                    self.numberOfSpots += len(layer.spotMU)
                    cumulativeMeterset += sum(layer.spotMU)
                    layer.cumulativeMeterset = cumulativeMeterset

                elif self.scanMode == "LINE":
                    # print("SpotNumber: ", dcm_layer[0x300b1092].value)
                    # print("SpotValue: ", np.frombuffer(dcm_layer[0x300b1094].value, dtype=np.float32).tolist())
                    # print("MUValue: ", np.frombuffer(dcm_layer[0x300b1096].value, dtype=np.float32).tolist())
                    # print("SizeValue: ", np.frombuffer(dcm_layer[0x300b1098].value, dtype=np.float32).tolist())
                    # print("PaintValue: ", dcm_layer[0x300b109a].value)
                    lineScanPoints = np.frombuffer(dcmLayer[0x300b1094].value, dtype=np.float32).tolist()
                    layer.lineScanControlPointX = lineScanPoints[0::2]
                    layer.lineScanControlPointY = lineScanPoints[1::2]
                    layer.lineScanControlPointWeights = np.frombuffer(dcmLayer[0x300b1096].value,
                                                                      dtype=np.float32).tolist()
                    # weights are converted to MU
                    layer.lineScanControlPointMU = np.array(
                        layer.lineScanControlPointWeights) * beam.beamMeterset / beam.finalCumulativeMetersetWeight
                    if layer.lineScanControlPointMU.size == 1:
                        layer.lineScanControlPointMU = [layer.lineScanControlPointMU]
                    else:
                        layer.lineScanControlPointMU = layer.lineScanControlPointMU.tolist()

                if beam.rangeShifterType != "none":
                    if hasattr(dcmLayer, 'RangeShifterSettingsSequence'):
                        rangeShifterSetting = dcmLayer.RangeShifterSettingsSequence[0].rangeShifterSetting
                        referencedRangeShifterNumber = dcmLayer.RangeShifterSettingsSequence[
                            0].referencedRangeShifterNumber
                        if hasattr(dcmLayer.RangeShifterSettingsSequence[0], 'IsocenterToRangeShifterDistance'):
                            isocenterToRangeShifterDistance = dcmLayer.RangeShifterSettingsSequence[
                                0].isocenterToRangeShifterDistance
                        if hasattr(dcmLayer.RangeShifterSettingsSequence[0], 'RangeShifterWaterEquivalentThickness'):
                            rangeShifterWaterEquivalentThickness = float(
                                dcmLayer.RangeShifterSettingsSequence[0].rangeShifterWaterEquivalentThickness)

                    layer.rangeShifterSetting = rangeShifterSetting
                    layer.isocenterToRangeShifterDistance = isocenterToRangeShifterDistance
                    layer.rangeShifterWaterEquivalentThickness = rangeShifterWaterEquivalentThickness
                    layer.referencedRangeShifterNumber = referencedRangeShifterNumber

                beam.layers.append(layer)

            self.beams.append(beam)

        self.isLoaded = 1

    def convertLineScanningToPBS(self, spotDensity=10):  # SpotDensity: number of simulated spots per cm.
        if self.scanMode != "LINE":
            logger.error("Scan mode " + self.scanMode + " cannot be converted to PBS plan")
            return

        self.numberOfSpots = 0

        for beam in self.beams:
            beam.finalCumulativeMetersetWeight = 0
            beam.beamMeterset = 0

            for layer in beam.layers:
                layer.scanSpotPositionMapX = []
                layer.scanSpotPositionMapY = []
                layer.scanSpotMetersetWeights = []
                layer.spotMU = []

                for i in range(len(layer.lineScanControlPointX) - 1):
                    x_start = layer.lineScanControlPointX[i]  # mm
                    x_stop = layer.lineScanControlPointX[i + 1]  # mm
                    y_start = layer.lineScanControlPointY[i]  # mm
                    y_stop = layer.lineScanControlPointY[i + 1]  # mm
                    distance = math.sqrt((x_stop - x_start) ** 2 + (y_stop - y_start) ** 2) / 10  # cm
                    numSpots = math.ceil(distance * spotDensity)
                    spotWeight = layer.lineScanControlPointWeights[i + 1] / numSpots
                    spotMU = layer.lineScanControlPointMU[i + 1] / numSpots

                    layer.scanSpotPositionMapX.extend(np.linspace(x_start, x_stop, num=numSpots))
                    layer.scanSpotPositionMapY.extend(np.linspace(y_start, y_stop, num=numSpots))
                    layer.scanSpotMetersetWeights.extend([spotWeight] * numSpots)
                    layer.spotMU.extend([spotMU] * numSpots)
                    self.numberOfSpots += numSpots

                beam.beamMeterset += sum(layer.spotMU)
                beam.finalCumulativeMetersetWeight += sum(layer.scanSpotMetersetWeights)

                layer.cumulativeMeterset = beam.beamMeterset

        self.scanMode = "MODULATED"
        logger.info("Line scanning plan converted to PBS plan with spot density of {} spots per cm.".format(spotDensity))

    def rotateVector(self, vec, angle, axis):
        global x, y, z
        if axis == 'x':
            x = vec[0]
            y = vec[1] * math.cos(angle) - vec[2] * math.sin(angle)
            z = vec[1] * math.sin(angle) + vec[2] * math.cos(angle)
        elif axis == 'y':
            x = vec[0] * math.cos(angle) + vec[2] * math.sin(angle)
            y = vec[1]
            z = -vec[0] * math.sin(angle) + vec[2] * math.cos(angle)
        elif axis == 'z':
            x = vec[0] * math.cos(angle) - vec[1] * math.sin(angle)
            y = vec[0] * math.sin(angle) + vec[1] * math.cos(angle)
            z = vec[2]

        return [x, y, z]

    def computeCartesianCoordinates(self, ct, scanner, beams, rangeShifters=[]):
        timeStart = time.time()

        spr = SPRimage()
        spr.convertCTToSPR(ct, scanner)

        ctBordersX = [spr.imagePositionPatient[0], spr.imagePositionPatient[0] + spr.gridSize[0] * spr.pixelSpacing[0]]
        ctBordersY = [spr.imagePositionPatient[1], spr.imagePositionPatient[1] + spr.gridSize[1] * spr.pixelSpacing[1]]
        ctBordersZ = [spr.imagePositionPatient[2], spr.imagePositionPatient[2] + spr.gridSize[2] * spr.pixelSpacing[2]]

        spotPositions = []
        spotDirections = []
        spotRanges = []

        # initialize spot info for raytracing
        for b in beams:
            beam = self.beams[b]

            rangeShifter = -1
            if beam.rangeShifterType == "binary":
                rangeShifter = next((rs for rs in rangeShifters if rs.id == beam.rangeShifterID), -1)

            for layer in beam.Layers:

                rangeInWater = spr.energyToRange(layer.nominalBeamEnergy) * 10
                if layer.rangeShifterSetting == 'IN':
                    if layer.rangeShifterWaterEquivalentThickness != "":
                        rangeShifterWET = layer.rangeShifterWaterEquivalentThickness
                    elif rangeShifter != -1:
                        rangeShifterWET = rangeShifter.wet
                    else:
                        rangeShifterWET = 0.0

                    if rangeShifterWET <= 0.0: continue
                    rangeInWater -= rangeShifterWET

                for s in range(len(layer.scanSpotPositionMapX)):
                    # BEV coordinates to 3D coordinates: position (x,y,z) and direction (u,v,w)
                    x, y, z = layer.scanSpotPositionMapX[s], 0, layer.scanSpotPositionMapY[s]
                    u, v, w = 1e-10, 1.0, 1e-10

                    # rotation for gantry angle (around Z axis)
                    angle = math.radians(beam.gantryAngle)
                    [x, y, z] = self.rotateVector([x, y, z], angle, 'z')
                    [u, v, w] = self.rotateVector([u, v, w], angle, 'z')

                    # rotation for couch angle (around Y axis)
                    angle = math.radians(beam.patientSupportAngle)
                    [x, y, z] = self.rotateVector([x, y, z], angle, 'y')
                    [u, v, w] = self.rotateVector([u, v, w], angle, 'y')

                    # Dicom CT coordinates
                    x = x + beam.isocenterPosition[0]
                    y = y + beam.isocenterPosition[1]
                    z = z + beam.isocenterPosition[2]

                    # translate initial position at the CT image border
                    translation = np.array([1.0, 1.0, 1.0])
                    translation[0] = (x - ctBordersX[int(u < 0)]) / u
                    translation[1] = (y - ctBordersY[int(v < 0)]) / v
                    translation[2] = (z - ctBordersZ[int(w < 0)]) / w
                    translation = translation[np.argmin(np.absolute(translation))]
                    x = x - translation * u
                    y = y - translation * v
                    z = z - translation * w

                    # append data to the list of spots to process
                    spotPositions.append([x, y, z])
                    spotDirections.append([u, v, w])
                    spotRanges.append(rangeInWater)

        cartesianSpotPositions = computePositionFromRange(spr, spotPositions, spotDirections, spotRanges)

        logger.info("Spot RayTracing: " + str(time.time() - timeStart) + " sec")
        return cartesianSpotPositions

    def updateSpotWeights(self, newWeights):
        # update weight of initial plan with those from PlanPencil
        count = 0
        self.deliveredProtons = 0
        self.totalMeterset = 0
        for beam in self.beams:
            beam.finalCumulativeMetersetWeight = 0
            beam.beamMeterset = 0
            for layer in beam.layers:
                for s in range(len(layer.spotMU)):
                    layer.scanSpotMetersetWeights[s] = newWeights[count]
                    layer.spotMU[s] = newWeights[count]
                    count += 1

                self.totalMeterset += sum(layer.spotMU)
                beam.beamMeterset += sum(layer.spotMU)
                beam.finalCumulativeMetersetWeight += sum(layer.spotMU)
                layer.cumulativeMeterset = beam.beamMeterset

    def getSpotWeights(self):
        spotWeights = np.zeros(self.numberOfSpots)
        count = 0
        for beam in self.beams:
            for layer in beam.layers:
                for s in range(len(layer.spotMU)):
                    spotWeights[count] = layer.spotMU[s]
                    count += 1
        return spotWeights

    def exportDicomWithNewUID(self, outputFile):
        # generate new uid
        initialUID = self.originalDicomDataset.SOPInstanceUID
        newUID = pydicom.uid.generate_uid()
        self.originalDicomDataset.SOPInstanceUID = newUID

        # save dicom file
        logger.info("Export dicom RTPLAN: " + outputFile)
        self.originalDicomDataset.save_as(outputFile)

        # restore initial uid
        self.originalDicomDataset.SOPInstanceUID = initialUID

        return newUID

    def save(self, filePath):
        if self.beamlets:
            self.beamlets.unload()

        for scenario in self.scenarios:
            scenario.unload()

        dcm = self.originalDicomDataset
        self.originalDicomDataset = []

        with open(filePath, 'wb') as fid:
            pickle.dump(self.__dict__, fid)

        self.originalDicomDataset = dcm

    def load(self, file_path):
        with open(file_path, 'rb') as fid:
            tmp = pickle.load(fid)

        self.__dict__.update(tmp)

    def copy(self):
        return copy.deepcopy(self)  # recursive copy

    def reorderPlan(self, orderLayers="decreasing", orderSpots="scanAlgo"):
        for i in range(len(self.beams)):
            if orderLayers == "decreasing":
                self.beams[i].reorderLayers(orderLayers)
            if orderSpots == "scanAlgo":
                for l in range(len(self.beams[i].layers)):
                    self.beams[i].layers[l].reorderSpots(orderSpots)


class PlanIonBeam:

    def __init__(self, fromBeam={}):
        if fromBeam == {}:
            self.seriesInstanceUID = ""
            self.beamName = ""
            self.isocenterPosition = [0, 0, 0]
            self.gantryAngle = 0.0
            self.patientSupportAngle = 0.0
            self.rangeShifterID = ""
            self.rangeShifterType = "none"
            self.finalCumulativeMetersetWeight = 0.0
            self.beamMeterset = 0.0
            self.layers = []
        else:
            self.seriesInstanceUID = fromBeam.seriesInstanceUID
            self.beamName = fromBeam.beamName
            self.isocenterPosition = list(fromBeam.isocenterPosition)
            self.gantryAngle = fromBeam.gantryAngle
            self.patientSupportAngle = fromBeam.patientSupportAngle
            self.rangeShifterID = fromBeam.rangeShifterID
            self.rangeShifterType = fromBeam.rangeShifterType
            self.finalCumulativeMetersetWeight = fromBeam.finalCumulativeMetersetWeight
            self.beamMeterset = fromBeam.beamMeterset
            self.layers = list(fromBeam.layers)

    def reorderLayers(self, order):
        layerEnergies = [self.layers[i].nominalBeamEnergy for i in range(len(self.layers))]
        if order == "decreasing":
            order = np.argsort(layerEnergies)[::-1]

        # order is a list
        self.layers = [self.layers[i] for i in order]


class PlanIonLayer:

    def __init__(self, fromLayer={}):
        self.lineScanControlPointLinearMU = None
        self.lineScanControlPointLinearWeights = None
        if fromLayer == {}:
            self.seriesInstanceUID = ""
            self.numberOfPaintings = 1
            self.nominalBeamEnergy = 0.0
            self.scanSpotPositionMapX = []
            self.scanSpotPositionMapY = []
            self.scanSpotMetersetWeights = []
            self.spotMU = []
            self.spotTiming = []
            self.cumulativeMeterset = 0.0
            self.rangeShifterSetting = 'OUT'
            self.isocenterToRangeShifterDistance = 0.0
            self.rangeShifterWaterEquivalentThickness = 0.0
            self.referencedRangeShifterNumber = 0
            self.lineScanControlPointX = []
            self.lineScanControlPointY = []
            self.lineScanControlPointWeights = []
            self.lineScanControlPointMU = []
        else:
            self.seriesInstanceUID = fromLayer.seriesInstanceUID
            self.numberOfPaintings = fromLayer.numberOfPaintings
            self.nominalBeamEnergy = fromLayer.nominalBeamEnergy
            self.scanSpotPositionMapX = list(fromLayer.scanSpotPositionMap_x)
            self.scanSpotPositionMapY = list(fromLayer.scanSpotPositionMap_y)
            self.scanSpotMetersetWeights = list(fromLayer.scanSpotMetersetWeights)
            self.spotMU = list(fromLayer.spotMU)
            if hasattr(fromLayer, 'SpotTiming'):
                self.spotTiming = list(fromLayer.SpotTiming)
            else:
                self.spotTiming = []
            self.cumulativeMeterset = fromLayer.cumulativeMeterset
            self.rangeShifterSetting = fromLayer.rangeShifterSetting
            self.isocenterToRangeShifterDistance = fromLayer.isocenterToRangeShifterDistance
            self.rangeShifterWaterEquivalentThickness = fromLayer.rangeShifterWaterEquivalentThickness
            self.referencedRangeShifterNumber = fromLayer.referencedRangeShifterNumber
            self.lineScanControlPointX = list(fromLayer.lineScanControlPointX)
            self.lineScanControlPointY = list(fromLayer.lineScanControlPointY)
            self.lineScanControlPointWeights = list(fromLayer.lineScanControlPointWeights)
            self.lineScanControlPointMU = list(fromLayer.lineScanControlPointMU)

    def reorderSpots(self, order):
        if type(order) is str and order == 'scanAlgo':
            coord = np.column_stack((self.scanSpotPositionMapX, self.scanSpotPositionMapY)).astype(float)
            order = np.argsort(coord.view('f8,f8'), order=['f1', 'f0'], axis=0).ravel()  # sort according to y then x
            coord = coord[order]
            _, indUnique = np.unique(coord[:, 1], return_index=True)  # unique y's
            nUnique = len(indUnique)
            if nUnique > 1:
                for i in range(1, nUnique):
                    if i == nUnique - 1:
                        indLastXAtCurrentY = coord.shape[0]
                    else:
                        indLastXAtCurrentY = indUnique[i + 1] - 1
                    if indUnique[i] == indLastXAtCurrentY:  # only 1 spot for current y coord
                        continue

                    coordLastXAtCurrentY = coord[indLastXAtCurrentY, 0]
                    indPrevious = indUnique[i] - 1
                    coordPrevious = coord[indPrevious, 0]
                    indFirstXAtCurrentY = indUnique[i]
                    coordFirstXAtCurrentY = coord[indFirstXAtCurrentY, 0]

                    # Check closest point to coord_previous
                    if np.abs(coordPrevious - coordFirstXAtCurrentY) > np.abs(
                            coordPrevious - coordLastXAtCurrentY):
                        # Need to inverse the order of the spot irradiated for those coordinates:
                        order[indFirstXAtCurrentY:indLastXAtCurrentY] = order[
                                                                        indFirstXAtCurrentY:indLastXAtCurrentY][
                                                                        ::-1]
                        coord[indFirstXAtCurrentY:indLastXAtCurrentY] = coord[
                                                                        indFirstXAtCurrentY:indLastXAtCurrentY][
                                                                        ::-1]

        # order is a list of the order of the spot irradiated
        # sort all lists according to order
        n = len(order)
        self.scanSpotPositionMapX = [self.scanSpotPositionMapX[i] for i in order]
        self.scanSpotPositionMapY = [self.scanSpotPositionMapY[i] for i in order]
        self.scanSpotMetersetWeights = [self.scanSpotMetersetWeights[i] for i in order]
        self.spotMU = [self.spotMU[i] for i in order]
        if len(self.spotTiming) == n:
            self.spotTiming = [self.spotTiming[i] for i in order]
        if hasattr(self, 'lineScanControlPointX') and len(self.lineScanControlPointX) == n:
            self.lineScanControlPointX = [self.lineScanControlPointX[i] for i in order]
        if hasattr(self, 'lineScanControlPointY') and len(self.lineScanControlPointY) == n:
            self.lineScanControlPointY = [self.lineScanControlPointY[i] for i in order]
        if hasattr(self, 'lineScanControlPointLinearWeights') and len(self.lineScanControlPointLinearWeights) == n:
            self.lineScanControlPointLinearWeights = [self.lineScanControlPointLinearWeights[i] for i in order]
        if hasattr(self, 'lineScanControlPointLinearMU') and len(self.lineScanControlPointLinearMU) == n:
            self.lineScanControlPointLinearMU = [self.lineScanControlPointLinearMU[i] for i in order]
