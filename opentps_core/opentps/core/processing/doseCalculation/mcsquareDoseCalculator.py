
import copy
import logging
import math
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence, Union, List, Any, Tuple

import numpy as np

from opentps.core.data.MCsquare import MCsquareConfig
from opentps.core.data import SparseBeamlets
from opentps.core.processing.planEvaluation.robustnessEvaluation import Robustness
from opentps.core.processing.doseCalculation.abstractDoseInfluenceCalculator import AbstractDoseInfluenceCalculator
from opentps.core.processing.doseCalculation.abstractMCDoseCalculator import AbstractMCDoseCalculator
from opentps.core.processing.imageProcessing import resampler3D
from opentps.core.utils.programSettings import ProgramSettings
from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.images import CTImage
from opentps.core.data.images import DoseImage
from opentps.core.data.images import LETImage
from opentps.core.data.images import Image3D
from opentps.core.data.images import ROIMask
from opentps.core.data.MCsquare import BDL
from opentps.core.data.plan import RTPlan
from opentps.core.data import ROIContour

import opentps.core.io.mcsquareIO as mcsquareIO

__all__ = ['MCsquareDoseCalculator']


logger = logging.getLogger(__name__)


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
        self._maxUncertainty = 2.0
        self._independentScoringGrid = False
        self._scoringVoxelSpacing = [2.0, 2.0, 2.0]
        self._simulationDirectory = ProgramSettings().simulationFolder
        self._simulationFolderName = 'MCsquare_simulation'

        # Robustness settings
        self.robustnessStrategy = "Disabled"
        self.setupSystematicError = [2.5, 2.5, 2.5]  # mm
        self.setupRandomError = [1.0, 1.0, 1.0]  # mm
        self.rangeSystematicError = 3.0  # %
        self._numScenarios = None

        self._computeDVHOnly = 0
        self._computeLETDistribution = 0

        self._subprocess = None
        self._subprocessKilled = True

        self.overwriteOutsideROI = None  # Previously cropCTContour but this name was confusing

        self._sparseLETFilePath = os.path.join(self._workDir, "Sparse_LET.txt")
        self._doseFilePath = os .path.join(self._workDir, "Dose.mhd")
        self._letFilePath = os.path.join(self._workDir, "LET.mhd")

        self._sparseDoseScenarioToRead = None

    @property
    def _sparseDoseFilePath(self):
        if self.robustnessStrategy== "Disabled":
            return os.path.join(self._workDir, "Sparse_Dose.txt")
        elif self._sparseDoseScenarioToRead==None:
            return os.path.join(self._workDir, "Sparse_Dose_Nominal.txt")
        else:
            return os.path.join(self._workDir, "Sparse_Dose_Scenario_" + str(self._sparseDoseScenarioToRead + 1) + "-" + str(
                self._numScenarios) + ".txt")


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
        if self.independentScoringGrid:
            return self._scoringVoxelSpacing
        else:
            return self._ct.spacing

    @scoringVoxelSpacing.setter
    def scoringVoxelSpacing(self, spacing: Union[float, Sequence[float]]):
        if np.isscalar(spacing):
            self._scoringVoxelSpacing = [spacing, spacing, spacing]
        else:
            self._scoringVoxelSpacing = spacing

    @property
    def scoringGridSize(self):
        if self.independentScoringGrid:
            return [int(math.floor(i / j * k)) for i, j, k in
                    zip(self._ct.gridSize, self.scoringVoxelSpacing, self._ct.spacing)]
        else:
            return self._ct.gridSize

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

    def computeDose(self, ct: CTImage, plan: RTPlan, roi: Optional[Sequence[ROIContour]] = None) -> DoseImage:
        logger.info("Prepare MCsquare Dose calculation")
        self._ct = ct
        self._plan = plan
        self._roi = roi
        self._config = self._doseComputationConfig

        self._writeFilesToSimuDir()
        self._cleanDir(self._workDir)
        self._startMCsquare()

        mhdDose = self._importDose()
        return mhdDose

    def computeDoseAndLET(self, ct: CTImage, plan: RTPlan, roi: Optional[Sequence[ROIContour]] = None) -> Tuple[DoseImage, LETImage]:
        self._computeLETDistribution = True
        dose = self.computeDose(ct, plan, roi)
        let = self._importLET()
        return dose, let

    def computeRobustScenario(self, ct: CTImage, plan: RTPlan, roi: [Sequence[Union[ROIContour, ROIMask]]]) -> Robustness:
        logger.info("Prepare MCsquare Robust Dose calculation")
        scenarios = Robustness()
        if self.robustnessStrategy == "DoseSpace":
            scenarios.selectionStrategy = "Dosimetric"
        else:
            scenarios.selectionStrategy = "Error"
        scenarios.setupSystematicError = self.setupSystematicError
        scenarios.setupRandomError = self.setupRandomError
        scenarios.rangeSystematicError = self.rangeSystematicError

        self._ct = ct
        self._plan = plan
        self._roi = roi
        # Generate MCsquare configuration file
        self._config = self._doseComputationConfig
        # Export useful data
        self._writeFilesToSimuDir()
        self._cleanDir(self._workDir)
        # Start nominal simulation
        logger.info("Simulation of nominal scenario")
        self._startMCsquare()
        dose = self._importDose()
        scenarios.setNominal(dose, self._roi)
        # Use special config for robustness
        self._config = self._scenarioComputationConfig
        # Export useful data
        self._writeFilesToSimuDir()
        # Start simulation of error scenarios
        logger.info("Simulation of error scenarios")
        self._startMCsquare()
        # Import dose results
        for s in range(self._numScenarios):
            fileName = 'Dose_Scenario_' + str(s + 1) + '-' + str(self._numScenarios) + '.mhd'
            self._doseFilePath = os.path.join(self._workDir, fileName)
            if os.path.isfile(self._doseFilePath):
                dose = self._importDose()
                scenarios.addScenario(dose, self._roi)

        return scenarios

    def computeBeamlets(self, ct: CTImage, plan: RTPlan, roi: Optional[Sequence[Union[ROIContour, ROIMask]]] = None) -> SparseBeamlets:
        logger.info("Prepare MCsquare Beamlet calculation")
        self._ct = ct
        self._plan = self._setPlanWeightsTo1(plan)
        self._roi = roi
        self._config = self._beamletComputationConfig

        self._writeFilesToSimuDir()
        self._cleanDir(self._workDir)
        self._startMCsquare()

        beamletDose = self._importBeamlets()
        beamletDose.beamletWeights = np.array(plan.spotMUs)

        return beamletDose

    def computeBeamletsAndLET(self, ct: CTImage, plan: RTPlan, roi: Optional[Sequence[Union[ROIContour, ROIMask]]] = None) -> Tuple[SparseBeamlets, SparseBeamlets]:
        self._computeLETDistribution = True

        beamletDose = self.computeBeamlets(ct, plan, roi)
        beamletLET = self._importBeamletsLET()

        return beamletDose, beamletLET

    def computeRobustScenarioBeamlets(self, ct:CTImage, plan:RTPlan, \
                                      roi:Optional[Sequence[Union[ROIContour, ROIMask]]]=None, storePath:Optional[str] = None) \
            -> Tuple[SparseBeamlets, Sequence[SparseBeamlets]]:

        nominal = self.computeBeamlets(ct, plan, roi)
        if not (storePath is None):
            outputBeamletFile = os.path.join(storePath, "BeamletMatrix_" + plan.seriesInstanceUID + "_Nominal.blm")
            nominal.storeOnFS(outputBeamletFile)

        scenarios = []
        for s in range(self._numScenarios):
            self._sparseDoseScenarioToRead = s
            scenario = self._importBeamlets()
            if not (storePath is None):
                outputBeamletFile = os.path.join(storePath,
                                                 "BeamletMatrix_" + plan.seriesInstanceUID + "_Scenario_" + str(
                                                     s + 1) + "-" + str(self._numScenarios) + ".blm")
                scenario.storeOnFS(outputBeamletFile)
            scenarios.append(scenario)

        return nominal, scenarios

    def optimizeBeamletFree(self, ct: CTImage, plan: RTPlan, roi: [Sequence[Union[ROIContour, ROIMask]]]) -> DoseImage:
        self._ct = ct
        self._plan = self._setPlanWeightsTo1(plan)
        # Generate MCsquare configuration file
        self._config = self._beamletFreeOptiConfig
        # Export useful data
        self._writeFilesToSimuDir()
        mcsquareIO.writeObjectives(self._plan.planDesign.objectives, self._objFilePath)
        for contour in roi:
            if isinstance(contour, ROIContour):
                mask = contour.getBinaryMask(self._ct.origin, self._ct.gridSize, self._ct.spacing)
            else:
                mask = contour
            mcsquareIO.writeContours(mask, self._contourFolderPath)
        self._cleanDir(self._workDir)
        # Start simulation
        self._startMCsquare(opti=True)

        # Import optimized plan
        file_path = os.path.join(self._mcsquareSimuDir, "Outputs", "Optimized_Plan.txt")
        mcsquareIO.updateWeightsFromPlanPencil(self._ct, self._plan, file_path, self.beamModel)

        doseImage = self._importDose(plan)
        return doseImage

    def _setPlanWeightsTo1(self, plan):
        plan = copy.deepcopy(plan)
        plan.spotMUs = np.ones(plan.spotMUs.shape)

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
        logger.info("Start MCsquare simulation")
        if platform.system() == "Linux":
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
        elif platform.system() == "Windows":
            if not opti:
                self._subprocess = subprocess.Popen(os.path.join(self._mcsquareSimuDir, "MCsquare_win.bat"),
                                                    cwd=self._mcsquareSimuDir)
            else:
                raise Exception('MCsquare opti not available on Windows.')
            self._subprocess.wait()
            if self._subprocessKilled:
                self._subprocessKilled = False
                raise Exception('MCsquare subprocess killed by caller.')
            self._subprocess = None

    def _importDose(self, plan:RTPlan = None) -> DoseImage:
        dose = mcsquareIO.readDose(self._doseFilePath)
        dose.patient = self._ct.patient
        if plan is None:
            fraction = 1.
        else:
            fraction = plan.numberOfFractionsPlanned
        dose.imageArray = dose.imageArray * self._deliveredProtons() * 1.602176e-19 * 1000 * fraction

        return dose

    def _importLET(self) -> LETImage:
        from opentps.core.data.images import LETImage
        return LETImage.fromImage3D(mcsquareIO.readMCsquareMHD(self._letFilePath))

    def _deliveredProtons(self) -> float:
        deliveredProtons = 0.
        for beam in self._plan:
            for layer in beam:
                Protons_per_MU = self._beamModel.computeMU2Protons(layer.nominalEnergy)
                deliveredProtons += layer.meterset * Protons_per_MU

        return deliveredProtons

    def _importBeamlets(self):
        self._resampleROI()
        beamletDose = mcsquareIO.readBeamlets(self._sparseDoseFilePath, self._beamletRescaling(), self._roi)
        return beamletDose

    def _importBeamletsLET(self):
        self._resampleROI()
        beamletDose = mcsquareIO.readBeamlets(self._sparseLETFilePath, self._beamletRescaling(), self._roi)
        return beamletDose

    def _beamletRescaling(self) -> Sequence[float]:
        beamletRescaling = []
        for beam in self._plan:
            for layer in beam:
                Protons_per_MU = self._beamModel.computeMU2Protons(layer.nominalEnergy)
                for spot in layer.spotMUs:
                    beamletRescaling.append(Protons_per_MU * 1.602176e-19 * 1000)

        return beamletRescaling

    @property
    def _mcsquareSimuDir(self):
        folder = os.path.join(self._simulationDirectory, self._simulationFolderName)
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def simulationFolderName(self):
        return self._simulationFolderName

    @simulationFolderName.setter
    def simulationFolderName(self, name):
        self._simulationFolderName = name

    @property
    def _workDir(self):
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
    def _doseComputationConfig(self) -> MCsquareConfig:
        config = self._generalMCsquareConfig

        config["Dose_to_Water_conversion"] = "OnlineSPR"

        return config

    @property
    def _scenarioComputationConfig(self) -> MCsquareConfig:
        config = self._generalMCsquareConfig
        config["Dose_to_Water_conversion"] = "OnlineSPR"
        # Import number of particles from previous simulation
        self.SimulatedParticles, self.SimulatedStatUncert = self.getSimulationProgress()
        config["Num_Primaries"] = self.SimulatedParticles
        config["Compute_stat_uncertainty"] = False
        config["Robustness_Mode"] = True
        config["Simulate_nominal_plan"] = False
        config["Systematic_Setup_Error"] = [self.setupSystematicError[0] / 10, self.setupSystematicError[1] / 10,
                                            self.setupSystematicError[2] / 10]  # cm
        config["Random_Setup_Error"] = [self.setupRandomError[0] / 10, self.setupRandomError[1] / 10,
                                        self.setupRandomError[2] / 10]  # cm
        config["Systematic_Range_Error"] = self.rangeSystematicError  # %
        if self.robustnessStrategy == "DoseSpace":
            config["Scenario_selection"] = "Random"
            config["Num_Random_Scenarios"] = 100
            self._numScenarios = config["Num_Random_Scenarios"]
        else:
            config["Scenario_selection"] = "All"
            self._numScenarios = 81

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
        config["Dose_Sparse_Threshold"] = 20000.0
        if self._computeLETDistribution > 0: config["LET_Sparse_Output"] = True
        # Robustness settings
        if self.robustnessStrategy == "Disabled":
            config["Robustness_Mode"] = False
        else:
            config["Robustness_Mode"] = True
            config["Simulate_nominal_plan"] = True
            config["Systematic_Setup_Error"] = [self.setupSystematicError[0] / 10,
                                                self.setupSystematicError[1] / 10,
                                                self.setupSystematicError[2] / 10]  # cm
            config["Random_Setup_Error"] = [self.setupRandomError[0] / 10, self.setupRandomError[1] / 10,
                                            self.setupRandomError[2] / 10]  # cm
            config["Systematic_Range_Error"] = self.rangeSystematicError  # %
            config[
                "Scenario_selection"] = "ReducedSet"  # "All" (81 scenarios), or "ReducedSet" (21 scenarios as in RayStation)
            if config["Scenario_selection"] == "All":
                self._numScenarios = 81
            else:
                self._numScenarios = 21

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
        config["Stat_uncertainty"] = self._maxUncertainty
        config["WorkDir"] = self._mcsquareSimuDir
        config["CT_File"] = self._ctName
        config["ScannerDirectory"] = self._scannerFolder  # ??? Required???
        config["HU_Density_Conversion_File"] = os.path.join(self._scannerFolder, "HU_Density_Conversion.txt")
        config["HU_Material_Conversion_File"] = os.path.join(self._scannerFolder, "HU_Material_Conversion.txt")
        config["BDL_Machine_Parameter_File"] = self._bdlFilePath
        config["BDL_Plan_File"] = self._planFilePath
        if self._computeDVHOnly > 0:
            config["Dose_MHD_Output"] = False
            config["Compute_DVH"] = True
        if self._computeLETDistribution > 0:
            config["LET_MHD_Output"] = True

        if self._independentScoringGrid:
            config["Independent_scoring_grid"] = True
            config["Scoring_voxel_spacing"] = [x / 10.0 for x in self.scoringVoxelSpacing]  # in cm
            config["Scoring_grid_size"] = self.scoringGridSize
            config["Scoring_origin"][0] = self._ct.origin[0] - config["Scoring_voxel_spacing"][
                0] / 2.0
            config["Scoring_origin"][2] = self._ct.origin[2] - config["Scoring_voxel_spacing"][
                2] / 2.0
            # config["Scoring_origin"][1] = -self._ct.origin[1] - config["Scoring_voxel_spacing"][1] * \
            #                              config["Scoring_grid_size"][1] + \
            #                              config["Scoring_voxel_spacing"][1] / 2.0
            config["Scoring_origin"][1] = self._ct.origin[1] - config["Scoring_voxel_spacing"][
                1] / 2.0
            config["Scoring_origin"][:] = [x / 10.0 for x in config["Scoring_origin"]]  # in cm
        # config["Stat_uncertainty"] = 2.

        return config

    def getSimulationProgress(self):
        progressionFile = os.path.join(self._workDir, "Simulation_progress.txt")

        simulationStarted = 0
        batch = 0
        uncertainty = -1
        multiplier = 1.0

        with open(progressionFile, 'r') as fid:
            for line in fid:
                if "Simulation started (" in line:
                    simulationStarted = 0
                    batch = 0
                    uncertainty = -1
                    multiplier = 1.0

                elif "batch " in line and " completed" in line:
                    tmp = line.split(' ')
                    if tmp[1].isnumeric(): batch = int(tmp[1])
                    if len(tmp) >= 6: uncertainty = float(tmp[5])

                elif "10x more particles per batch" in line:
                    multiplier *= 10.0

        numParticles = int(batch * multiplier * self._nbPrimaries / 10.0)
        return numParticles, uncertainty

    def _resampleROI(self):
        if self._roi is None or not self._roi:
            return

        roiResampled = []
        for contour in self._roi:
            if isinstance(contour, ROIContour):
                resampledMask = contour.getBinaryMask(origin=self._ct.origin, gridSize=self.scoringGridSize,
                                                      spacing=np.array(self.scoringVoxelSpacing))
            elif isinstance(contour, ROIMask):
                resampledMask = resampler3D.resampleImage3D(contour, origin=self._ct.origin,
                                                            gridSize=self.scoringGridSize,
                                                            spacing=np.array(self.scoringVoxelSpacing))
            else:
                raise Exception(contour.__class__.__name__ + ' is not a supported class for roi')
            resampledMask.patient = None
            roiResampled.append(resampledMask)
        self._roi = roiResampled
        self._roi[0].patient = self._ct.patient

    def _createFolderIfNotExists(self, folder):
        folder = Path(folder)

        if not folder.is_dir():
            os.mkdir(folder)
