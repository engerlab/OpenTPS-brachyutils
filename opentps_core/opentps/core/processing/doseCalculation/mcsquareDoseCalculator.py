
import copy
import logging
import math
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence, Union, Tuple

import numpy as np

from opentps.core.data.MCsquare import MCsquareConfig
from opentps.core.data import SparseBeamlets
from opentps.core.processing.planEvaluation.robustnessEvaluation import RobustnessEval
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
from opentps.core.data.plan import PlanDesign
from opentps.core.data import ROIContour

import opentps.core.io.mcsquareIO as mcsquareIO

__all__ = ['MCsquareDoseCalculator']

from scipy.sparse import csc_matrix

logger = logging.getLogger(__name__)


class MCsquareDoseCalculator(AbstractMCDoseCalculator, AbstractDoseInfluenceCalculator):
    """
    Class for Monte Carlo dose calculation using MCsquare.
    This class is a wrapper for the MCsquare dose calculation engine.

    Attributes
    ----------
    _ctCalibration : AbstractCTCalibration
        CT calibration (Optional)
    _ct : Image3D
        the CT image of the patient (Optional)
    _plan : RTPlan
        Treatment plan (Optional)
    _roi : ROIMask
        ROI mask
    _config : MCsquareConfig
        MCsquare configuration
    _mcsquareCTCalibration : BDL
        MCsquare CT calibration
    _beamModel : BDL
        MCsquare beam model
    _nbPrimaries : int
        Number of primaries proton
    _statUncertainty : float
        Statistical uncertainty for MCsquare
    _scoringVoxelSpacing : float
        Scoring voxel spacing of dose image
    _simulationDirectory : str
        Simulation directory path
    _simulationFolderName : str
        Simulation folder name
    _computeDVHOnly : int
        Compute DVH only (True if > 0)
    _computeLETDistribution : int
        Compute Linear Energy transfer (LET) distribution in the patient (True if > 0)
    _subprocess : subprocess.Popen
        Subprocess if used
    _subprocessKilled : bool
        Subprocess killed (if subprocess is used)
    _sparseLETFilePath : str
        Sparse LET file path
    _sparseDoseFilePath : str
        Sparse dose file path
    _sparseDoseScenarioToRead : int
        Sparse dose scenario to read
    """
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
        self._statUncertainty = 0.0
        self._scoringVoxelSpacing = None
        self._scoringGridSize = None
        self._scoringOrigin = None
        self._adapt_gridSize_to_new_spacing=False
        self._simulationDirectory = ProgramSettings().simulationFolder
        self._simulationFolderName = 'MCsquare_simulation'

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
        if (self._plan.planDesign is None) or self._plan.planDesign.robustness.selectionStrategy==self._plan.planDesign.robustness.Strategies.DISABLED:
            return os.path.join(self._workDir, "Sparse_Dose.txt")
        elif self._sparseDoseScenarioToRead==None:
            return os.path.join(self._workDir, "Sparse_Dose_Nominal.txt")
        else:
            return os.path.join(self._workDir, "Sparse_Dose_Scenario_" + str(self._sparseDoseScenarioToRead + 1) + "-" + str(
                self._plan.planDesign.robustness.numScenarios) + ".txt")


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
        self._nbPrimaries = int(primaries)

    @property
    def statUncertainty(self) -> float:
        return self._statUncertainty

    @statUncertainty.setter
    def statUncertainty(self, uncertainty: float):
        self._statUncertainty = uncertainty

    @property
    def independentScoringGrid(self) -> bool:
        return not np.allclose(self._ct.spacing, self.scoringVoxelSpacing, atol=0.01) or \
                not np.allclose(self._ct.gridSize, self.scoringGridSize, atol=0.01) or \
                not np.allclose(self._ct.origin, self.scoringOrigin, atol=0.01)

    @property
    def scoringVoxelSpacing(self) -> Sequence[float]:
        if self._scoringVoxelSpacing is not None:
            return self._scoringVoxelSpacing
        
        if self._plan:
            if self._plan.planDesign:
                return self._plan.planDesign.scoringVoxelSpacing

        if self._ct:
            return self._ct.spacing

    @scoringVoxelSpacing.setter
    def scoringVoxelSpacing(self, spacing: Union[float, Sequence[float]]):
        if np.isscalar(spacing):
            self._scoringVoxelSpacing = [spacing, spacing, spacing]
        else:
            self._scoringVoxelSpacing = spacing

    @property
    def scoringGridSize(self):
        if self._scoringGridSize is not None:
            return self._scoringGridSize
        if self._plan:
            if self._plan.planDesign:
                return self._plan.planDesign.scoringGridSize
        if self._ct:
            return self._ct.gridSize
    
    @scoringGridSize.setter
    def scoringGridSize(self, gridSize):
        self._scoringGridSize = gridSize
    
    @property
    def scoringOrigin(self):
        if self._scoringOrigin is not None:
            return self._scoringOrigin             
        if self._plan:
            if self._plan.planDesign:
                return self._plan.planDesign.scoringOrigin
        if self._ct:
                return self._ct.origin
        
    @scoringOrigin.setter
    def scoringOrigin(self, origin):
        self._scoringOrigin = origin

    @property
    def ct(self):
        return self._ct
    
    @ct.setter
    def ct(self, ctImage):
        self._ct = ctImage
        if self._adapt_gridSize_to_new_spacing and self._scoringVoxelSpacing is not None:
            self.setScoringParameters(scoringSpacing=self._scoringVoxelSpacing, adapt_gridSize_to_new_spacing=True)

    def setScoringParameters(self, scoringGridSize:Optional[Sequence[int]]=None, scoringSpacing:Optional[Sequence[float]]=None,
                                scoringOrigin:Optional[Sequence[int]]=None, adapt_gridSize_to_new_spacing=False):
        """
        Sets the scoring parameters

        Parameters
        ----------
        scoringGridSize: Sequence[int]
            scoring grid size
        scoringSpacing: Sequence[float]
            scoring spacing
        scoringOrigin: Sequence[float]
            scoring origin
        adapt_gridSize_to_new_spacing: bool
            If True, automatically adapt the gridSize to the new spacing
        """
        if adapt_gridSize_to_new_spacing and scoringGridSize is not None:
            raise ValueError('Cannot adapt gridSize to new spacing if scoringGridSize provided.')
        
        if scoringSpacing is not None: self.scoringVoxelSpacing = scoringSpacing
        if scoringGridSize is not None: self.scoringGridSize = scoringGridSize
        if scoringOrigin is not None: self.scoringOrigin = scoringOrigin
        
        if adapt_gridSize_to_new_spacing and self._scoringVoxelSpacing is not None:
            self._adapt_gridSize_to_new_spacing = True
            if self._ct:
                newGridSize = np.floor(self._ct.gridSize*self._ct.spacing/self._scoringVoxelSpacing).astype(int)
                print(f"Adapting scoring gridSize to scoring spacing. Scoring gridSize = {newGridSize} while CT original gridSize is {self._ct.gridSize}")
                self.scoringGridSize = np.floor(self._ct.gridSize*self._ct.spacing/self._scoringVoxelSpacing).astype(int)
                self._adapt_gridSize_to_new_spacing = False

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
        """
        Compute dose distribution in the patient using MCsquare

        Parameters
        ----------
        ct : CTImage
            CT image of the patient
        plan : RTPlan
            RT plan
        roi : Optional[Sequence[ROIContour]], optional
            ROI contours, by default None

        Returns
        -------
        DoseImage
            Dose distribution with same grid size and spacing as the CT image

        """
        logger.info("Prepare MCsquare Dose calculation")
        self.ct = ct
        self._plan = plan
        self._roi = roi
        self._config = self._doseComputationConfig

        self._writeFilesToSimuDir()
        self._cleanDir(self._workDir)
        self._startMCsquare()

        mhdDose = self._importDose(plan)
        return mhdDose

    def computeDoseAndLET(self, ct: CTImage, plan: RTPlan, roi: Optional[Sequence[ROIContour]] = None) -> Tuple[DoseImage, LETImage]:
        """
        Compute dose and LET distribution in the patient using MCsquare

        Parameters
        ----------
        ct : CTImage
            CT image of the patient
        plan : RTPlan
            RT plan
        roi : Optional[Sequence[ROIContour]], optional
            ROI contours, by default None

        Returns
        -------
        Tuple[DoseImage, LETImage]
            Dose and LET distribution with same grid size and spacing as the CT image
        """
        self._computeLETDistribution = True
        dose = self.computeDose(ct, plan, roi)
        let = self._importLET()
        return dose, let

    def computeRobustScenario(self, ct: CTImage, plan: RTPlan, roi: [Sequence[Union[ROIContour, ROIMask]]]) -> RobustnessEval:
        """
        Compute robustness scenario using MCsquare

        Parameters
        ----------
        ct : CTImage
            CT image of the patient
        plan : RTPlan
            RT plan
        roi : [Sequence[Union[ROIContour, ROIMask]]]
            ROI contours or masks

        Returns
        -------
        scenarios:Robustness
            Robustness with nominal and error scenarios
        """
        logger.info("Prepare MCsquare Robust Dose calculation")
        scenarios = plan.planDesign.robustnessEval

        self.ct = ct
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
        dose = self._importDose(plan)
        scenarios.setNominal(dose, self._roi)
        # Use special config for robustness
        self._config = self._scenarioComputationConfig
        # Export useful data
        self._writeFilesToSimuDir()
        # Start simulation of error scenarios
        logger.info("Simulation of error scenarios")
        self._startMCsquare()
        # Import dose results
        for s in range(self._plan.planDesign.robustnessEval.numScenarios):
            fileName = 'Dose_Scenario_' + str(s + 1) + '-' + str(self._plan.planDesign.robustnessEval.numScenarios) + '.mhd'
            self._doseFilePath = os.path.join(self._workDir, fileName)
            if os.path.isfile(self._doseFilePath):
                dose = self._importDose(plan)
                scenarios.addScenario(dose, self._roi)

        return scenarios

    def computeBeamlets(self, ct: CTImage, plan: RTPlan, roi: Optional[Sequence[Union[ROIContour, ROIMask]]] = None) -> SparseBeamlets:
        """
        Compute beamlets using MCsquare

        Parameters
        ----------
        ct : CTImage
            CT image of the patient
        plan : RTPlan
            RT plan
        roi : Optional[Sequence[Union[ROIContour, ROIMask]]], optional
            ROI contours or masks on which beamlets will be cropped at import, by default None

        Returns
        -------
        beamletDose:SparseBeamlets
            Beamlets dose with same grid size and spacing as the CT image
        """
        logger.info("Prepare MCsquare Beamlet calculation")
        self.ct = ct
        self._plan = copy.deepcopy(plan)
        self._plan.spotMUs = np.ones(self._plan.spotMUs.shape)
        self._roi = roi

        self._plan.simplify(threshold=None) # make sure no spot duplicates

        if not self._plan.planDesign: # external plan
            planDesign = PlanDesign()
            planDesign.ct = ct
            planDesign.targetMask = roi
            planDesign.scoringVoxelSpacing = self.scoringVoxelSpacing
            self._plan.planDesign = planDesign
            
        self._config = self._beamletComputationConfig

        self._writeFilesToSimuDir()
        self._cleanDir(self._workDir)

        if platform.system() == "Linux2":
            beamletDose = self._computeBeamletsLinux()
        else:
            self._startMCsquare()
            beamletDose = self._importBeamlets()

        return beamletDose

    def _computeBeamletsLinux(self):
        """
        Compute beamlets using MCsquare on Linux

        Returns
        -------
        beamletDose:SparseBeamlets
            Beamlets dose with same grid size and spacing as the CT image
        """
        os.environ['MCsquare_Materials_Dir'] = self._materialFolder
        nVoxels = self.scoringGridSize[0]*self.scoringGridSize[1]*self.scoringGridSize[2]

        from opentps.core.processing.doseCalculation._utils import MCsquareSharedLib
        self._mc2Lib = MCsquareSharedLib(mcsquarePath=self._mcsquareSimuDir)
        sparseBeamlets = self._mc2Lib.computeBeamletsSharedLib(self._configFilePath, nVoxels, self._plan.numberOfSpots)

        beamletDose = SparseBeamlets()
        beamletDose.setUnitaryBeamlets(
            csc_matrix.dot(sparseBeamlets, csc_matrix(np.diag(self._beamletRescaling()), dtype=np.float32)))

        beamletDose.doseOrigin = self.scoringOrigin

        beamletDose.doseSpacing = self.scoringVoxelSpacing
        beamletDose.doseGridSize = self.scoringGridSize
        return beamletDose

    def computeBeamletsAndLET(self, ct: CTImage, plan: RTPlan, roi: Optional[Sequence[Union[ROIContour, ROIMask]]] = None) -> Tuple[SparseBeamlets, SparseBeamlets]:
        """
        Compute beamlets and LET using MCsquare

        Parameters
        ----------
        ct : CTImage
            CT image of the patient
        plan : RTPlan
            RT plan
        roi : Optional[Sequence[Union[ROIContour, ROIMask]]], optional
            ROI contours or masks, by default None

        Returns
        -------
        beamletDose:SparseBeamlets
            Beamlets dose with same grid size and spacing as the CT image
        beamletLET:SparseBeamlets
            Beamlets LET with same grid size and spacing as the CT image
        """
        self._computeLETDistribution = True

        beamletDose = self.computeBeamlets(ct, plan, roi)
        beamletLET = self._importBeamletsLET()

        return beamletDose, beamletLET

    def computeRobustScenarioBeamlets(self, ct:CTImage, plan:RTPlan, \
                                      roi:Optional[Sequence[Union[ROIContour, ROIMask]]]=None, storePath:Optional[str] = None) \
            -> Tuple[SparseBeamlets, Sequence[SparseBeamlets]]:
        """
        Compute nominal and error scenarios beamlets using MCsquare

        Parameters
        ----------
        ct : CTImage
            CT image of the patient
        plan : RTPlan
            RT plan
        roi : Optional[Sequence[Union[ROIContour, ROIMask]]], optional
            ROI contours or masks on which beamlets will be cropped at import, by default None
        storePath : Optional[str], optional
            Path to store the beamlets, by default None

        Returns
        -------
        nominal:SparseBeamlets
            Nominal beamlets dose with same grid size and spacing as the CT image
        scenarios:Sequence[SparseBeamlets]
            Error scenarios beamlets dose with same grid size and spacing as the CT image
        """
        # TODO: Investigate this nominal scenario computation (necessary?)
        nominal = self.computeBeamlets(ct, plan, roi)
        if not (storePath is None):
            outputBeamletFile = os.path.join(storePath, "BeamletMatrix_" + plan.seriesInstanceUID + "_Nominal.blm")
            nominal.storeOnFS(outputBeamletFile)

        scenarios = []
        for s in range(self._plan.planDesign.robustness.numScenarios):
            self._sparseDoseScenarioToRead = s
            scenario = self._importBeamlets()
            if not (storePath is None):
                outputBeamletFile = os.path.join(storePath,
                                                 "BeamletMatrix_" + plan.seriesInstanceUID + "_Scenario_" + str(
                                                     s + 1) + "-" + str(self._plan.planDesign.robustness.numScenarios) + ".blm")
                scenario.storeOnFS(outputBeamletFile)
            scenarios.append(scenario)

        return nominal, scenarios

    def optimizeBeamletFree(self, ct: CTImage, plan: RTPlan, roi: [Sequence[Union[ROIContour, ROIMask]]]) -> DoseImage:
        """
        Optimize weights using beamlet free optimization

        Parameters
        ----------
        ct : CTImage
            CT image of the patient
        plan : RTPlan
            RT plan
        roi : [Sequence[Union[ROIContour, ROIMask]]]
            ROI contours or masks

        Returns
        -------
        DoseImage:doseImage
            Optimized dose
        """
        self.ct = ct
        self._plan = plan
        self._plan.spotMUs = np.ones(self._plan.spotMUs.shape)
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
        file_path = os.path.join(self._workDir, "Optimized_Plan.txt")
        mcsquareIO.updateWeightsFromPlanPencil(self._ct, self._plan, file_path, self.beamModel)
        doseImage = self._importDose(self._plan)

        return doseImage

    def _cleanDir(self, dirPath):
        """
        Clean given directory

        Parameters
        ----------
        dirPath : str
            Path to the directory to clean
        """
        if os.path.isdir(dirPath):
            shutil.rmtree(dirPath)

    def _writeFilesToSimuDir(self):
        """
        Write all files needed for MCsquare simulation in the simulation directory
        """
        self._cleanDir(self._materialFolder)
        self._cleanDir(self._scannerFolder)

        mcsquareIO.writeCT(self._ct, self._ctFilePath, self.overwriteOutsideROI)
        mcsquareIO.writePlan(self._plan, self._planFilePath, self._ct, self._beamModel)
        mcsquareIO.writeCTCalibrationAndBDL(self._ctCalibration, self._scannerFolder, self._materialFolder,
                                            self._beamModel, self._bdlFilePath)
        mcsquareIO.writeConfig(self._config, self._configFilePath)
        mcsquareIO.writeBin(self._mcsquareSimuDir)

    def _startMCsquare(self, opti=False):
        """
        Start MCsquare simulation
        """
        if not (self._subprocess is None):
            raise Exception("MCsquare already running")

        self._subprocessKilled = False
        logger.info("Start MCsquare simulation")
        if platform.system() == "Linux" or platform.system() == 'Darwin':
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
                self._subprocess = subprocess.Popen(os.path.join(self._mcsquareSimuDir, "MCsquare_opti_win.bat"),
                                                    cwd=self._mcsquareSimuDir)
            self._subprocess.wait()
            if self._subprocessKilled:
                self._subprocessKilled = False
                raise Exception('MCsquare subprocess killed by caller.')
            self._subprocess = None

    def _importDose(self, plan:RTPlan = None) -> DoseImage:
        """
        Import dose from MCsquare simulation

        Parameters
        ----------
        plan : RTPlan (optional)
            RT plan (default is None)
        """
        dose = mcsquareIO.readDose(self._doseFilePath)
        dose.patient = self._ct.patient
        if plan is None:
            fraction = 1.
        else:
            fraction = plan.numberOfFractionsPlanned
        dose.imageArray = dose.imageArray * self._deliveredProtons() * 1.602176e-19 * 1000 * fraction
        return dose

    def _importLET(self) -> LETImage:
        """
        Import LET from MCsquare simulation

        Returns
        -------
        LETImage
            LET image computed by MCsquare
        """
        from opentps.core.data.images import LETImage
        return LETImage.fromImage3D(mcsquareIO.readMCsquareMHD(self._letFilePath))

    def _deliveredProtons(self) -> float:
        """
        Compute the number of protons delivered in the plan

        Returns
        -------
        deliveredProtons float
            Number of protons delivered in the plan

        """
        deliveredProtons = 0.
        for beam in self._plan:
            for layer in beam:
                Protons_per_MU = self._beamModel.computeMU2Protons(layer.nominalEnergy)
                deliveredProtons += layer.meterset * Protons_per_MU

        return deliveredProtons

    def _importBeamlets(self):
        """
        Import beamlets from MCsquare simulation

        Returns
        -------
        beamletDose : BeamletDose
            Beamlet dose computed by MCsquare
        """
        self._resampleROI()
        beamletDose = mcsquareIO.readBeamlets(self._sparseDoseFilePath, self._beamletRescaling(), self.scoringOrigin, self._roi)
        return beamletDose

    def _importBeamletsLET(self):
        """
        Import beamlets LET from MCsquare simulation

        Returns
        -------
        beamletDose : BeamletDose
            Beamlet LET computed by MCsquare
        """
        self._resampleROI()
        beamletDose = mcsquareIO.readBeamlets(self._sparseLETFilePath, self._beamletRescaling(), self.scoringOrigin, self._roi)
        return beamletDose

    def _beamletRescaling(self) -> Sequence[float]:
        """
        Compute the beamlet rescaling factors

        Returns
        -------
        beamletRescaling : Sequence[float]
            Beamlet rescaling factors
        """
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
        config["Systematic_Setup_Error"] = [self._plan.planDesign.robustnessEval.setupSystematicError[0] / 10, self._plan.planDesign.robustnessEval.setupSystematicError[1] / 10,
                                            self._plan.planDesign.robustnessEval.setupSystematicError[2] / 10]  # cm
        config["Random_Setup_Error"] = [self._plan.planDesign.robustnessEval.setupRandomError[0] / 10, self._plan.planDesign.robustnessEval.setupRandomError[1] / 10,
                                        self._plan.planDesign.robustnessEval.setupRandomError[2] / 10]  # cm
        config["Systematic_Range_Error"] = self._plan.planDesign.robustnessEval.rangeSystematicError  # %
        
        # TODO: Remove duplicate of nominal scenario (in MCsquare or retrieving nominal scenario index from output MC2 file)
        #if np.sum(config["Random_Setup_Error"])==0:
        #    config["Simulate_nominal_plan"] = False 
        
        if self._plan.planDesign.robustnessEval.selectionStrategy == self._plan.planDesign.robustnessEval.Strategies.ALL:
            config["Scenario_selection"] == "All"
            self._plan.planDesign.robustnessEval.numScenarios = 81
            if(config["Systematic_Setup_Error"][0] == 0.0): self._plan.planDesign.robustnessEval.numScenarios/=3
            if(config["Systematic_Setup_Error"][1] == 0.0): self._plan.planDesign.robustnessEval.numScenarios/=3
            if(config["Systematic_Setup_Error"][2] == 0.0): self._plan.planDesign.robustnessEval.numScenarios/=3
            if(config["Systematic_Range_Error"] == 0.0): self._plan.planDesign.robustnessEval.numScenarios/=3

        elif self._plan.planDesign.robustnessEval.selectionStrategy == self._plan.planDesign.robustnessEval.Strategies.REDUCED_SET:
            config["Scenario_selection"] = "ReducedSet"  
            self._plan.planDesign.robustnessEval.numScenarios = 21
            if(config["Systematic_Setup_Error"][0] == 0.0): self._plan.planDesign.robustnessEval.numScenarios-= 6
            if(config["Systematic_Setup_Error"][1] == 0.0): self._plan.planDesign.robustnessEval.numScenarios-= 6
            if(config["Systematic_Setup_Error"][2] == 0.0): self._plan.planDesign.robustnessEval.numScenarios-=6
            if(config["Systematic_Range_Error"] == 0.0): self._plan.planDesign.robustnessEval.numScenarios/= 3

        elif self._plan.planDesign.robustnessEval.selectionStrategy == self._plan.planDesign.robustnessEval.Strategies.RANDOM:
            config["Scenario_selection"] = "Random" 
            if self._plan.planDesign.robustnessEval.numScenarios > 0: 
                config["Num_Random_Scenarios"] = self._plan.planDesign.robustnessEval.numScenarios # random
            else: config["Num_Random_Scenarios"] = 100 # Default
            self._plan.planDesign.robustnessEval.numScenarios = config["Num_Random_Scenarios"]
        else:
            logger.error("No scenario selection strategy was configured. Pick between [ALL,REDUCED_SET,RANDOM]")

        self._plan.planDesign.robustnessEval.numScenarios = int(self._plan.planDesign.robustnessEval.numScenarios) # handle float output
        
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
        if self._plan.planDesign.robustness.selectionStrategy == self._plan.planDesign.robustness.Strategies.DISABLED:
            config["Robustness_Mode"] = False
        else:
            config["Robustness_Mode"] = True
            config["Simulate_nominal_plan"] = True
            config["Systematic_Setup_Error"] = [self._plan.planDesign.robustness.setupSystematicError[0] / 10,
                                                self._plan.planDesign.robustness.setupSystematicError[1] / 10,
                                                self._plan.planDesign.robustness.setupSystematicError[2] / 10]  # cm
            config["Random_Setup_Error"] = [self._plan.planDesign.robustness.setupRandomError[0] / 10, self._plan.planDesign.robustness.setupRandomError[1] / 10,
                                            self._plan.planDesign.robustness.setupRandomError[2] / 10]  # cm
            config["Systematic_Range_Error"] = self._plan.planDesign.robustness.rangeSystematicError  # %
            
            # TO DO: Remove duplicate of nominal scenario (in MCsquare or retrieving nominal scenario index from output MC2 file)
            #if np.sum(config["Random_Setup_Error"])==0:
            #    config["Simulate_nominal_plan"] = False 

            if self._plan.planDesign.robustness.selectionStrategy == self._plan.planDesign.robustness.Strategies.ALL:
                config["Scenario_selection"] == "All"
                self._plan.planDesign.robustness.numScenarios = 81
                if(config["Systematic_Setup_Error"][0] == 0.0): self._plan.planDesign.robustness.numScenarios/=3
                if(config["Systematic_Setup_Error"][1] == 0.0): self._plan.planDesign.robustness.numScenarios/=3
                if(config["Systematic_Setup_Error"][2] == 0.0): self._plan.planDesign.robustness.numScenarios/=3
                if(config["Systematic_Range_Error"] == 0.0): self._plan.planDesign.robustness.numScenarios/=3
                    

            elif self._plan.planDesign.robustness.selectionStrategy == self._plan.planDesign.robustness.Strategies.REDUCED_SET:
                config["Scenario_selection"] = "ReducedSet"  
                self._plan.planDesign.robustness.numScenarios = 21
                if(config["Systematic_Setup_Error"][0] == 0.0): self._plan.planDesign.robustness.numScenarios-= 6
                if(config["Systematic_Setup_Error"][1] == 0.0): self._plan.planDesign.robustness.numScenarios-= 6
                if(config["Systematic_Setup_Error"][2] == 0.0): self._plan.planDesign.robustness.numScenarios-=6
                if(config["Systematic_Range_Error"] == 0.0): self._plan.planDesign.robustness.numScenarios/= 3


            elif self._plan.planDesign.robustness.selectionStrategy == self._plan.planDesign.robustness.Strategies.RANDOM:
                config["Scenario_selection"] = "Random"
                if self._plan.planDesign.robustness.numScenarios > 0: 
                    config["Num_Random_Scenarios"] = self._plan.planDesign.robustness.numScenarios # random 
                else: config["Num_Random_Scenarios"] = 100 # Default
                self._plan.planDesign.robustness.numScenarios = config["Num_Random_Scenarios"]
            else:
                logger.error("No scenario selection strategy was configured. Pick between [ALL,REDUCED_SET,RANDOM]")

            self._plan.planDesign.robustness.numScenarios = int(self._plan.planDesign.robustness.numScenarios) # handle float output

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
        config["Stat_uncertainty"] = self._statUncertainty
        config["WorkDir"] = self._mcsquareSimuDir
        config["CT_File"] = self._ctFilePath
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

        if self.independentScoringGrid:
            config["Independent_scoring_grid"] = True
            config["Scoring_voxel_spacing"] = [x / 10.0 for x in self.scoringVoxelSpacing]  # in cm
            config["Scoring_grid_size"] = self.scoringGridSize
            config["Scoring_origin"][0] = self.scoringOrigin[0] - self.scoringVoxelSpacing[
                0] / 2.0
            config["Scoring_origin"][2] = self.scoringOrigin[2] - self.scoringVoxelSpacing[
                2] / 2.0
            config["Scoring_origin"][1] = -self.scoringOrigin[1] - self.scoringVoxelSpacing[1] * \
                                         self.scoringGridSize[1] + \
                                         self.scoringVoxelSpacing[1] / 2.0 #  inversion of Y, which is flipped in MCsquare
            config["Scoring_origin"][:] = [x / 10.0 for x in config["Scoring_origin"]]  # in cm
        # config["Stat_uncertainty"] = 2.

        return config

    def getSimulationProgress(self):
        """
        Get the number of simulated particles and the uncertainty

        Returns
        -------
        numParticles : int
            Number of simulated particles
        uncertainty : float
            Uncertainty (%)
        """
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
        """
        Resample the ROI to the scoring grid
        """
        if self._roi is None or not self._roi:
            return

        if not(isinstance(self._roi, Sequence)):
            self._roi = [self._roi]

        roiResampled = []
        for contour in self._roi:
            if isinstance(contour, ROIContour):
                resampledMask = contour.getBinaryMask(origin=self.scoringOrigin, gridSize=self.scoringGridSize,
                                                      spacing=np.array(self.scoringVoxelSpacing))
            elif isinstance(contour, ROIMask):
                resampledMask = resampler3D.resampleImage3D(contour, origin=self.scoringOrigin,
                                                            gridSize=self.scoringGridSize,
                                                            spacing=np.array(self.scoringVoxelSpacing))
            else:
                raise Exception(contour.__class__.__name__ + ' is not a supported class for roi')
            resampledMask.patient = None
            roiResampled.append(resampledMask)
        self._roi = roiResampled

    def _createFolderIfNotExists(self, folder):
        """
        Create a folder if it does not exist

        Parameters
        ----------
        folder : str
            Folder path
        """
        folder = Path(folder)

        if not folder.is_dir():
            os.mkdir(folder)
