import copy
import os
import platform
import shutil
from math import sqrt
from typing import Optional, Sequence, Union

import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.ndimage import gaussian_filter, zoom

from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.MCsquare.mcsquareConfig import MCsquareConfig
from Core.Data.Plan.planIonBeam import PlanIonBeam
from Core.Data.Plan.planIonLayer import PlanIonLayer
from Core.Data.Plan.rtPlan import RTPlan
from Core.IO import mcsquareIO
from Core.Processing.DoseCalculation.mcsquareDoseCalculator import MCsquareDoseCalculator
from Core.Processing.ImageProcessing.imageTransform3D import ImageTransform3D
from Extensions.FLASH.Core.Processing.DoseCalculation.MCsquare.mcsquareFlashConfig import MCsquareFlashConfig


class FluenceBasedMCsquareDoseCalculator(MCsquareDoseCalculator):
    HU_AIR = -1024
    SPOT_WEIGHT_THRESHOLD = 0.02

    def __init__(self):
        super().__init__()

        self._distToIsocenter = 0.0

    @property
    def distanceToIsocenter(self) -> float:
        return self._distToIsocenter

    @distanceToIsocenter.setter
    def distanceToIsocenter(self, dist: float):
        self._distToIsocenter = dist

    def computeDose(self, ct:CTImage, plan: RTPlan) -> DoseImage:
        return super().computeDose(ct, self._fluencePlan(plan))

    def computeBeamlets(self, ct:CTImage, plan:RTPlan, roi:Optional[ROIMask] = None):
        self._ct = ct
        self._plan = self._fluencePlan(plan)
        self._roi = roi
        self._config = self._noSpotSizeConfig

        self._writeFilesToSimuDir()
        self._cleanDir(self._outputDir)
        self._startMCsquare()

        beamletDose = self._importBeamlets()
        beamletDose.beamletWeights = self._plan.weights

        return beamletDose

    def _fluencePlan_old(self, plan:RTPlan) -> RTPlan:
        newPlan = copy.deepcopy(plan)

        for beam in newPlan:
            ctBEV = ImageTransform3D.dicomToIECGantry(self._ct, beam, self.HU_AIR)
            isocenterBEV = ImageTransform3D.dicomCoordinate2iecGantry(self._ct, beam, beam.isocenterPosition)

            for layer in beam:
                fluence = self._layerFluenceAtIso(beam, layer, ctBEV)

                layer.removeSpot(layer.spotX, layer.spotY) # Empty layer
                fluenceX, fluenceY = np.meshgrid(range(fluence.shape[0]), range(fluence.shape[1]))

                for i in range(fluenceX.shape[0]):
                    for j in range(fluenceX.shape[1]):
                        if fluence[fluenceX[i, j], fluenceY[i, j]]>self.SPOT_WEIGHT_THRESHOLD:
                            pos = ctBEV.getPositionFromVoxelIndex((fluenceX[i, j], fluenceY[i, j], isocenterBEV[2]))
                            pos0 = pos[0] - isocenterBEV[0]
                            pos1 = -pos[1] + isocenterBEV[1]

                            layer.appendSpot(pos0, pos1, fluence[fluenceX[i, j], fluenceY[i, j]])
        return newPlan

    def _fluencePlan(self, plan:RTPlan) -> RTPlan:
        newPlan = copy.deepcopy(plan)

        for beam in newPlan:
            ctBEV = ImageTransform3D.dicomToIECGantry(self._ct, beam, self.HU_AIR)
            isocenterBEV = ImageTransform3D.dicomCoordinate2iecGantry(self._ct, beam, beam.isocenterPosition)

            for layer in beam:
                fluence = self._layerFluenceAtNozzle(beam, layer, ctBEV)

                fluence[fluence<self.SPOT_WEIGHT_THRESHOLD] = 0.
                #fluence = fluence*layer.meterset/np.sum(fluence)

                layer.removeSpot(layer.spotX, layer.spotY) # Empty layer
                fluenceX, fluenceY = np.meshgrid(range(fluence.shape[0]), range(fluence.shape[1]))

                for i in range(fluenceX.shape[0]):
                    for j in range(fluenceX.shape[1]):
                        if fluence[fluenceX[i, j], fluenceY[i, j]]:
                            posNozzle = ctBEV.getPositionFromVoxelIndex((fluenceX[i, j], fluenceY[i, j], isocenterBEV[2]))
                            pos0Nozzle = posNozzle[0] - isocenterBEV[0]
                            pos1Nozzle = -posNozzle[1] + isocenterBEV[1]

                            pos0Iso = pos0Nozzle*self.beamModel.smx/(self.beamModel.smx-self.beamModel.nozzle_isocenter)
                            pos1Iso = pos1Nozzle*self.beamModel.smy/(self.beamModel.smy-self.beamModel.nozzle_isocenter)

                            layer.appendSpot(pos0Iso, pos1Iso, fluence[fluenceX[i, j], fluenceY[i, j]])
        return newPlan

    def _layerFluenceAtNozzle(self, beam:PlanIonBeam, layer:PlanIonLayer, ctBEV:Image3D) -> np.ndarray:
        pointSpreadFluence = self._pointSpreadFluenceAtNozzle(beam, layer, ctBEV)

        sigmaX, sigmaY = self.beamModel.spotSizes(layer.nominalEnergy)
        sigmaX /= ctBEV.spacing[0]
        sigmaY /= ctBEV.spacing[1]

        # Cannot explain this
        sigmaX = sigmaX*(self.beamModel.smx-self.beamModel.nozzle_isocenter)/self.beamModel.smx
        sigmaY = sigmaY*(self.beamModel.smy-self.beamModel.nozzle_isocenter)/self.beamModel.smy

        fluence = gaussian_filter(pointSpreadFluence, [sigmaX, sigmaY], mode='constant', cval=0., truncate=4)

        return fluence

    def _layerFluenceAtIso(self, beam:PlanIonBeam, layer:PlanIonLayer, ctBEV:Image3D) -> np.ndarray:
        pointSpreadFluence = self._pointSpreadFluenceAtIso(beam, layer, ctBEV)

        sigmaX, sigmaY = self._spotSizeAtIso(layer.nominalEnergy)
        sigmaX /= ctBEV.spacing[0]
        sigmaY /= ctBEV.spacing[1]

        fluence = gaussian_filter(pointSpreadFluence, [sigmaX, sigmaY], mode='constant', cval=0., truncate=4)

        return fluence

    def _spotSizeAtIso(self, energy):
        divergenceX, divergenceY = self.beamModel.divergences(energy)
        corrX, corrY = self.beamModel.correlations(energy)
        sigmaX, sigmaY = self.beamModel.spotSizes(energy)

        z = self.beamModel.nozzle_isocenter

        partialCorrX0 = corrX*sigmaX + divergenceX*z
        partialCorrY0 = corrY*sigmaY + divergenceY*z

        sigmaX0 = sqrt(sigmaX*sigmaX + 2*partialCorrX0*divergenceX*z - divergenceX*divergenceX*z*z)
        sigmaY0 = sqrt(sigmaY * sigmaY + 2 * partialCorrY0 * divergenceY * z - divergenceY * divergenceY * z * z)

        return sigmaX0, sigmaY0

    def _pointSpreadFluenceAtIso(self, beam:PlanIonBeam, layer:PlanIonLayer, ctBEV:Image3D) -> np.ndarray:
        XYs = zip(layer.spotX, layer.spotY)

        isocenterBEV = ImageTransform3D.dicomCoordinate2iecGantry(self._ct, beam, beam.isocenterPosition)
        xyInds = [ctBEV.getVoxelIndexFromPosition(((isocenterBEV[0]+xy[0]), (isocenterBEV[1]-xy[1]), isocenterBEV[2])) for xy in XYs]

        fluence = np.zeros((ctBEV.imageArray.shape[0], ctBEV.imageArray.shape[1]))

        for i, weight in enumerate(layer.spotWeights):
            xyInd = xyInds[i]
            fluence[xyInd[0], xyInd[1]] = weight

        return fluence / (ctBEV.spacing[0] * ctBEV.spacing[1])

    def _pointSpreadFluenceAtNozzle(self, beam:PlanIonBeam, layer:PlanIonLayer, ctBEV:Image3D) -> np.ndarray:
        isocenterBEV = ImageTransform3D.dicomCoordinate2iecGantry(self._ct, beam, beam.isocenterPosition)

        fluence = np.zeros((ctBEV.imageArray.shape[0], ctBEV.imageArray.shape[1]))

        for i, x in enumerate(layer.spotX):
            y = layer.spotY[i]
            spotWeight = layer.spotWeights[i]

            xAtNozzle = x*(self.beamModel.smx-self.beamModel.nozzle_isocenter)/self.beamModel.smx
            yAtNozzle = y*(self.beamModel.smy-self.beamModel.nozzle_isocenter)/self.beamModel.smy

            ind = ctBEV.getVoxelIndexFromPosition(((isocenterBEV[0] + xAtNozzle), (isocenterBEV[1] - yAtNozzle), isocenterBEV[2]))
            fluence[ind[0], ind[1]] = spotWeight

        return fluence / (ctBEV.spacing[0] * ctBEV.spacing[1])

    @property
    def _noSpotSizeConfig(self) -> MCsquareFlashConfig:
        config = MCsquareFlashConfig()

        config["Num_Primaries"] = self._nbPrimaries
        config["WorkDir"] = self._mcsquareSimuDir
        config["CT_File"] = self._ctName
        config["ScannerDirectory"] = self._scannerFolder  # ??? Required???
        config["HU_Density_Conversion_File"] = os.path.join(self._scannerFolder, "HU_Density_Conversion.txt")
        config["HU_Material_Conversion_File"] = os.path.join(self._scannerFolder, "HU_Material_Conversion.txt")
        config["BDL_Machine_Parameter_File"] = self._bdlFilePath
        config["BDL_Plan_File"] = self._planFilePath

        config["Dose_to_Water_conversion"] = "OnlineSPR"
        config["Compute_stat_uncertainty"] = False
        config["Beamlet_Mode"] = True
        config["Beamlet_Parallelization"] = True
        config["Dose_MHD_Output"] = False
        config["Dose_Sparse_Output"] = True

        config["Dose_Sparse_Threshold"] = 20000

        config["NoSpotSize"] = True

        print(config)
        return config

    def _writeFilesToSimuDir(self):
        self._cleanDir(self._materialFolder)
        self._cleanDir(self._scannerFolder)

        mcsquareIO.writeCT(self._ct, self._ctFilePath)
        mcsquareIO.writePlan(self._plan, self._planFilePath, self._ct, self._beamModel)
        mcsquareIO.writeBDL(self._beamModel, self._bdlFilePath)
        mcsquareIO.writeCTCalibration(self._ctCalibration, self._scannerFolder, self._materialFolder)
        mcsquareIO.writeConfig(self._config, self._configFilePath)
        self._writeBin() # We export the FLASH specific version of MCsquare

    def _writeBin(self):
        destFolder = self._mcsquareSimuDir

        import Extensions.FLASH.Core.Processing.DoseCalculation.MCsquare as MCsquareModule
        mcsquarePath = str(MCsquareModule.__path__[0])

        if (platform.system() == "Linux"):
            source_path = os.path.join(mcsquarePath, "MCsquare")
            destination_path = os.path.join(destFolder, "MCsquare")
            shutil.copyfile(source_path, destination_path)  # copy file
            shutil.copymode(source_path, destination_path)  # copy permissions

            source_path = os.path.join(mcsquarePath, "MCsquare_linux")
            destination_path = os.path.join(destFolder, "MCsquare_linux")
            shutil.copyfile(source_path, destination_path)
            shutil.copymode(source_path, destination_path)
        else:
            raise Exception("Error: Operating system " + platform.system() + " is not supported by MCsquare.")
