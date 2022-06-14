import copy
import math
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.image3D import Image3D
from Core.Data.Images.roiMask import ROIMask
from Core.Data.MCsquare.bdl import BDL
from Core.Data.MCsquare.mcsquareConfig import MCsquareConfig
from Core.Data.Plan.rtPlan import RTPlan
from Core.Data.roiContour import ROIContour
from Core.Data.sparseBeamlets import SparseBeamlets
from Core.Processing.DoseCalculation.abstractDoseInfluenceCalculator import AbstractDoseInfluenceCalculator
from Core.Processing.DoseCalculation.abstractMCDoseCalculator import AbstractMCDoseCalculator
from programSettings import ProgramSettings

import Core.IO.mcsquareIO as mcsquareIO


class MCsquareDoseCalculator(AbstractMCDoseCalculator, AbstractDoseInfluenceCalculator):
    def __init__(self):
        AbstractMCDoseCalculator.__init__(self)
        AbstractDoseInfluenceCalculator.__init__(self)

        self._ctCalibration: Optional[AbstractCTCalibration] = None
        self._ct: Optional[Image3D] = None
        self._plan: Optional[RTPlan] = None
        self._roi = None
        self._config = None
        self._mcsquareCTCalibration = None
        self._beamModel = None
        self._nbPrimaries = 0
        self._independentScoringGrid = False
        self._scoringVoxelSpacing = [2.0, 2.0, 2.0]
        self._simulationDirectory = ProgramSettings().simulationFolder

        self._subprocess = None
        self._subprocessKilled = True

        self.overwriteOutsideROI = None  # Previously cropCTContour but this name was confusing

    @property
    def ctCalibration(self) -> Optional[AbstractCTCalibration]:
        return self._ctCalibration

    @ctCalibration.setter
    def ctCalibration(self, ctCalibration: AbstractCTCalibration):
        self._ctCalibration = ctCalibration

    @property
    def beamModel(self) -> BDL:
        return self._beamModel

    @beamModel.setter
    def beamModel(self, beamModel: BDL):
        self._beamModel = beamModel

    @property
    def nbPrimaries(self) -> int:
        return self._nbPrimaries

    @nbPrimaries.setter
    def nbPrimaries(self, primaries: int):
        self._nbPrimaries = primaries

    @property
    def independentScoringGrid(self) -> bool:
        return self._independentScoringGrid

    @independentScoringGrid.setter
    def independentScoringGrid(self, independent: bool):
        self._independentScoringGrid = independent

    @property
    def scoringVoxelSpacing(self) -> Sequence[float]:
        return self._scoringVoxelSpacing

    @scoringVoxelSpacing.setter
    def scoringVoxelSpacing(self, spacing: Sequence[float]):
        self._scoringVoxelSpacing = spacing

    @property
    def simulationDirectory(self) -> str:
        return str(self._simulationDirectory)

    @simulationDirectory.setter
    def simulationDirectory(self, path):
        self._simulationDirectory = path

    def kill(self):
        if not (self._subprocess is None):
            self._subprocessKilled = True
            self._subprocess.kill()
            self._subprocess = None

    def computeDose(self, ct: CTImage, plan: RTPlan) -> DoseImage:
        self._ct = ct
        self._plan = plan
        self._config = self._doseComputationConfig

        self._writeFilesToSimuDir()
        self._cleanDir(self._outputDir)
        self._startMCsquare()

        doseImage = self._importDose()

        return doseImage

    def computeBeamlets(self, ct: CTImage, plan: RTPlan, roi: Optional[ROIMask] = None) -> SparseBeamlets:
        self._ct = ct
        self._plan = self._setPlanWeightsTo1(plan)
        self._roi = roi
        self._config = self._beamletComputationConfig

        self._writeFilesToSimuDir()
        self._cleanDir(self._outputDir)
        self._startMCsquare()

        beamletDose = self._importBeamlets()
        beamletDose.beamletWeights = np.array(plan.spotWeights)

        return beamletDose

    def optimizeBeamletFree(self, ct: CTImage, plan: RTPlan, contours: Sequence[ROIMask]) -> DoseImage:
        self._ct = ct
        self._plan = self._setPlanWeightsTo1(plan)
        # Generate MCsquare configuration file
        self._config = self._beamletFreeOptiConfig
        # Export useful data
        self._writeFilesToSimuDir()
        mcsquareIO.writeObjectives(self._plan.objectives, self._objFilePath)
        for contour in contours:
            mcsquareIO.writeContours(contour, self._contourFolderPath)
        self._cleanDir(self._outputDir)
        # Start simulation
        self._startMCsquare(opti=True)

        # Import optimized plan
        file_path = os.path.join(self._mcsquareSimuDir, "Outputs", "Optimized_Plan.txt")
        #mcsquareIO.updateWeightsFromPlanPencil(self._ct, self._plan, file_path, self.beamModel)

        doseImage = self._importDose()
        return doseImage

    def _setPlanWeightsTo1(self, plan):
        plan = copy.deepcopy(plan)
        plan.spotWeights = np.ones(plan.spotWeights.shape)

        return plan

    def _cleanDir(self, dirPath):
        if os.path.isdir(dirPath):
            shutil.rmtree(dirPath)

    def _writeFilesToSimuDir(self):
        self._cleanDir(self._materialFolder)
        self._cleanDir(self._scannerFolder)

        mcsquareIO.writeCT(self._ct, self._ctFilePath, self.overwriteOutsideROI)
        mcsquareIO.writePlan(self._plan, self._planFilePath, self._ct, self._beamModel)
        mcsquareIO.writeCTCalibrationAndBDL(self._ctCalibration, self._scannerFolder, self._materialFolder,
                                            self._beamModel, self._bdlFilePath)
        mcsquareIO.writeConfig(self._config, self._configFilePath)
        mcsquareIO.writeBin(self._mcsquareSimuDir)

    def _startMCsquare(self, opti=False):
        if not (self._subprocess is None):
            raise Exception("MCsquare already running")

        self._subprocessKilled = False

        if (platform.system() == "Linux"):
            if not opti:
                self._subprocess = subprocess.Popen(["sh", "MCsquare"], cwd=self._mcsquareSimuDir)
            else:
                self._subprocess = subprocess.Popen(["sh", "MCsquare_opti"], cwd=self._mcsquareSimuDir)
            self._subprocess.wait()
            if self._subprocessKilled:
                self._subprocessKilled = False
                raise Exception('MCsquare subprocess killed by caller.')
            self._subprocess = None
            # os.system("cd " + self._mcsquareSimuDir + " && sh MCsquare")
        elif (platform.system() == "Windows"):
            if not opti:
                os.system("cd " + self._mcsquareSimuDir + " && MCsquare_win.bat")
            else:
                os.system("cd " + self._mcsquareSimuDir + " && MCsquare_opti_win.bat")

    def _importDose(self) -> DoseImage:
        dose = mcsquareIO.readDose(self._doseFilePath)
        dose.patient = self._ct.patient
        print(self._deliveredProtons())
        dose.imageArray = dose.imageArray * self._deliveredProtons() * 1.602176e-19 * 1000

        return dose

    def _deliveredProtons(self) -> float:
        deliveredProtons = 0.
        for beam in self._plan:
            for layer in beam:
                Protons_per_MU = self._beamModel.computeMU2Protons(layer.nominalEnergy)
                deliveredProtons += layer.meterset * Protons_per_MU

        return deliveredProtons

    def _importBeamlets(self):
        beamletDose = mcsquareIO.readBeamlets(self._sparseDoseFilePath, self._roi)
        beamletDose.beamletRescaling = self._beamletRescaling()
        return beamletDose

    def _beamletRescaling(self):
        beamletRescaling = []
        for beam in self._plan:
            for layer in beam:
                Protons_per_MU = self._beamModel.computeMU2Protons(layer.nominalEnergy)
                for spot in layer.spotWeights:
                    beamletRescaling.append(Protons_per_MU * 1.602176e-19 * 1000)

        return beamletRescaling

    @property
    def _mcsquareSimuDir(self):
        folder = os.path.join(self._simulationDirectory, 'MCsquare_simulation')
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def _outputDir(self):
        folder = os.path.join(self._mcsquareSimuDir, 'Outputs')
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def _ctFilePath(self):
        return os.path.join(self._mcsquareSimuDir, self._ctName)

    @property
    def _ctName(self):
        return 'CT.mhd'

    @property
    def _planFilePath(self):
        return os.path.join(self._mcsquareSimuDir, 'PlanPencil.txt')

    @property
    def _configFilePath(self):
        return os.path.join(self._mcsquareSimuDir, 'config.txt')

    @property
    def _objFilePath(self):
        return os.path.join(self._mcsquareSimuDir, 'PlanObjectives.txt')

    @property
    def _contourFolderPath(self):
        return os.path.join(self._mcsquareSimuDir, "structs")

    @property
    def _bdlFilePath(self):
        return os.path.join(self._mcsquareSimuDir, 'bdl.txt')

    @property
    def _materialFolder(self):
        folder = os.path.join(self._mcsquareSimuDir, 'Materials')
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def _scannerFolder(self):
        folder = os.path.join(self._mcsquareSimuDir, 'Scanner')
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def _doseFilePath(self):
        return os.path.join(self._outputDir, "Dose.mhd")

    @property
    def _sparseDoseFilePath(self):
        return os.path.join(self._outputDir, "Sparse_Dose.txt")

    @property
    def _doseComputationConfig(self) -> MCsquareConfig:
        config = self._generalMCsquareConfig

        config["Dose_to_Water_conversion"] = "OnlineSPR"

        return config

    @property
    def _beamletComputationConfig(self) -> MCsquareConfig:
        config = self._generalMCsquareConfig

        config["Dose_to_Water_conversion"] = "OnlineSPR"
        config["Compute_stat_uncertainty"] = False
        config["Beamlet_Mode"] = True
        config["Beamlet_Parallelization"] = True
        config["Dose_MHD_Output"] = False
        config["Dose_Sparse_Output"] = True

        return config

    @property
    def _beamletFreeOptiConfig(self) -> MCsquareConfig:
        config = self._generalMCsquareConfig

        config["Dose_to_Water_conversion"] = "OnlineSPR"
        config["Compute_stat_uncertainty"] = False
        config["Optimization_Mode"] = True
        config["Dose_MHD_Output"] = True

        return config

    @property
    def _generalMCsquareConfig(self) -> MCsquareConfig:
        config = MCsquareConfig()

        config["Num_Primaries"] = self._nbPrimaries
        config["WorkDir"] = self._mcsquareSimuDir
        config["CT_File"] = self._ctName
        config["ScannerDirectory"] = self._scannerFolder  # ??? Required???
        config["HU_Density_Conversion_File"] = os.path.join(self._scannerFolder, "HU_Density_Conversion.txt")
        config["HU_Material_Conversion_File"] = os.path.join(self._scannerFolder, "HU_Material_Conversion.txt")
        config["BDL_Machine_Parameter_File"] = self._bdlFilePath
        config["BDL_Plan_File"] = self._planFilePath
        if self._independentScoringGrid == True:
            config["Independent_scoring_grid"] = True
            config["Scoring_voxel_spacing"] = self._scoringVoxelSpacing  # in mm
            config["Scoring_grid_size"] = [int(math.floor(i / j * k)) for i, j, k in
                                           zip(self._ct.gridSize, config["Scoring_voxel_spacing"], self._ct.spacing)]
            config["Scoring_origin"] = [0, 0, 0]
            config["Scoring_origin"][0] = self._ct.angles[0] - config["Scoring_voxel_spacing"][
                0] / 2.0
            config["Scoring_origin"][2] = self._ct.angles[2] - config["Scoring_voxel_spacing"][
                2] / 2.0
            #config["Scoring_origin"][1] = -self._ct.angles[1] - config["Scoring_voxel_spacing"][1] * \
            #                              config["Scoring_grid_size"][1] + \
            #                              config["Scoring_voxel_spacing"][1] / 2.0
            config["Scoring_origin"][1] = self._ct.angles[1] - config["Scoring_voxel_spacing"][
                1] / 2.0

            from Core.Processing.ImageProcessing import sitkImageProcessing
            sitkImageProcessing.resize(self._roi, np.array(self.scoringVoxelSpacing), self._ct.origin,
                                       config["Scoring_grid_size"])
            config["Scoring_origin"][:] = [x / 10.0 for x in config["Scoring_origin"]]  # in cm
            config["Scoring_voxel_spacing"][:] = [x / 10.0 for x in config["Scoring_voxel_spacing"]]  # in cm

        # config["Stat_uncertainty"] = 2.

        return config

    def _createFolderIfNotExists(self, folder):
        folder = Path(folder)

        if not folder.is_dir():
            os.mkdir(folder)
