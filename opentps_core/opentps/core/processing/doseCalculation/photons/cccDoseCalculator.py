
import copy
import logging
import math
import os
import platform
import shutil
import subprocess
import scipy as sp
import time
import numpy as np

from pathlib import Path
from typing import Optional, Sequence, Union
from typing import Optional, Sequence, Union, Dict, Any

from opentps.core.data.images import DoseImage
from opentps.core.data import SparseBeamlets
from opentps.core.processing.doseCalculation.abstractDoseCalculator import AbstractDoseCalculator
from opentps.core.utils.programSettings import ProgramSettings
from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.images import CTImage
from opentps.core.data.images import Image3D
from opentps.core.data.images import ROIMask
from opentps.core.data import ROIContour
from opentps.core.data.plan._photonPlan import PhotonPlan
import opentps.core.io.CCCdoseEngineIO as CCCdoseEngineIO
from opentps.core.processing.doseCalculation.photons._utils import shiftBeamlets, adjustDoseToScenario
from opentps.core.data.plan._robustnessPhoton import RobustScenario
from scipy.ndimage import gaussian_filter


__all__ = ['CCCDoseCalculator']


logger = logging.getLogger(__name__)


class CCCDoseCalculator(AbstractDoseCalculator):
    """
    Class for Collapse Cone Convolution dose calculation algorithm using WiscPlan Engine.
    This class is a wrapper for the Collapse Cone Convolution dose calculation algorithm.

    Attributes
    ----------
    _ctCalibration : AbstractCTCalibration
        CT calibration (Optional)
    _ct : Image3D
        the CT image of the patient (Optional)
    _plan : PhotonPlan
        Treatment plan (Optional)
    _roi : ROIMask
        ROI mask
    _simulationDirectory : str
        Simulation directory path
    _simulationFolderName : str
        Simulation folder name
    batchSize : int
        number of processes created in the cpu to calculate the dose
    _subprocess : subprocess.Popen
        Subprocess if used
    _subprocessKilled : bool
        Subprocess killed (if subprocess is used)
    overwriteOutsideROI : bool
        if true, set to air all the region in the CT outside the ROI
    self.WorkSpaceDir : str
        Path to the directory where the opentps code was cloned
    self.ROFolder : str
        Name of the folder where robust scenarios are stored
        
    """
    def __init__(self, batchSize = 1):

        self._ctCalibration: Optional[AbstractCTCalibration] = None
        self._ct: Optional[Image3D] = None
        self._plan: Optional[PhotonPlan] = None
        self._roi = None
        self._simulationDirectory = ProgramSettings().simulationFolder
        self._simulationFolderName = 'CCC_simulation'
        self.batchSize = batchSize

        self._subprocess = []
        self._subprocessKilled = True

        self.overwriteOutsideROI = None  

        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.WorkSpaceDir = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir, os.pardir, os.pardir, os.pardir))
        self.ROFolder = ''
    
    @property
    def _CCCSimuDir(self):
        folder = os.path.join(self._simulationDirectory, self._simulationFolderName, self.ROFolder)
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def outputDir(self):
        folder = os.path.join(self._CCCSimuDir, 'Outputs')
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def _executableDir(self):
        dir = os.path.join(self._CCCSimuDir, 'execFiles')
        self._createFolderIfNotExists(dir)
        return dir

    @property
    def _ctName(self):
        return 'Geometry'
    
    @property
    def _ctDirName(self):
        ctDir = os.path.join(self._CCCSimuDir, self._ctName)
        self._createFolderIfNotExists(ctDir)
        return ctDir
    
    @property
    def _beamDirectory(self):
        dir = os.path.join(self._CCCSimuDir, 'BeamSpecs')
        self._createFolderIfNotExists(dir)
        return dir
    
    @property
    def _CCCexecutablePath(self):
        return os.path.join(self.WorkSpaceDir,'opentps','core','processing','doseCalculation','photons','CCC_DoseEngine', 'CCC_DoseEngine')
    
    @property
    def ctCalibration(self) -> Optional[AbstractCTCalibration]:
        return self._ctCalibration

    @ctCalibration.setter
    def ctCalibration(self, ctCalibration: AbstractCTCalibration):
        self._ctCalibration = ctCalibration

    def createKernelFilePath(self):
        """
        Write the kernel file paths into a txt file which is stored into the simulation folder. This is required for the CCC dose calculation.
        """
        kernelsDir = os.path.join(self.WorkSpaceDir,'opentps','core','processing','doseCalculation','photons','Kernels_differentFluence')
        f = open(os.path.join(self._CCCSimuDir, 'kernelPaths.txt'),'w')
        for fileName in os.listdir(kernelsDir):
            split = fileName.split('.')
            if split[-1] == 'txt':
                f.write(split[0]+'\n')
            else:
                f.write('kernel_'+split[0]+'\n')
            f.write(os.path.join(kernelsDir, fileName)+'\n')                

    @property
    def _kernelsFilePath(self):
        kernelFilePath = os.path.join(self._CCCSimuDir, 'kernelPaths.txt')
        # if not os.path.isfile(kernelFilePath):
        self.createKernelFilePath()
        return kernelFilePath

    def createGeometryFilePath(self):
        f = open(os.path.join(self._CCCSimuDir, 'geometryFilePath.txt'),'w')
        f.write('geometry_header\n'+os.path.join(self._ctDirName, 'CT_HeaderFile.txt\n'))
        f.write('geometry_density\n'+os.path.join(self._ctDirName, 'CT.bin\n'))
  

    @property
    def _geometryFilePath(self):
        geometryFilePath = os.path.join(self._CCCSimuDir, 'geometryFilePath.txt')
        if not os.path.isfile(geometryFilePath):
            self.createGeometryFilePath()
        return geometryFilePath
    
    def _createFolderIfNotExists(self, folder):
        folder = Path(folder)
        if not folder.is_dir():
            os.makedirs(folder)
    
    def writeExecuteCCCfile(self):
        for batch in range(self.batchSize):
            f = open(os.path.join(self._executableDir, 'CCC_simulation_batch{}'.format(batch)),'w')
            f.write('{executablePath} {kernelFilePath} {geometryFilePath} {beamPath} {outputPath}'.format(executablePath = self._CCCexecutablePath, kernelFilePath = self._kernelsFilePath, geometryFilePath = self._geometryFilePath, beamPath = os.path.join(self._beamDirectory,'pencilBeamSpecs_batch{}.txt'.format(batch)), outputPath = os.path.join(self.outputDir,'sparseBeamletMatrix_batch{}.bin'.format(batch))))
            f.close()


    def _writeFilesToSimuDir(self):
        CCCdoseEngineIO.writeCT(self._ct, self._ctDirName, self._plan.beams[0].isocenterPosition_mm, self.overwriteOutsideROI)
        CCCdoseEngineIO.writePlan(self._plan, self._beamDirectory, self.batchSize) 



    def _cleanDir(self, dirPath):
        if os.path.isdir(dirPath):
            shutil.rmtree(dirPath)

    def _startCCC(self, opti=False):
        if len(self._subprocess) > 0:
            raise Exception("CCC already running")

        self._subprocessKilled = False
        logger.info("Start CCC simulation")
        if platform.system() == "Linux":
            for batch in range(self.batchSize):
                if not opti:
                    self._subprocess.append(subprocess.Popen(["sh", 'CCC_simulation_batch{}'.format(batch)], cwd=self._executableDir))
                else:
                    self._subprocess.append(subprocess.Popen(["sh", 'CCC_simulation_opti_batch{}'.format(batch)], cwd=self._executableDir))
            for process in self._subprocess:
                process.wait()

            if self._subprocessKilled:
                self._subprocessKilled = False
                raise Exception('Collapse Cone Convolution subprocess killed by caller.')
            self._subprocess = []


    def _importBeamlets(self):
        beamletDose = CCCdoseEngineIO.readBeamlets(os.path.join(self._ctDirName, 'CT_HeaderFile.txt'), self.outputDir, self.batchSize, self._roi)
        return beamletDose

    def _importDose(self):
        beamletDose = CCCdoseEngineIO.readDose(os.path.join(self._ctDirName, 'CT_HeaderFile.txt'), self.outputDir, self.batchSize, self._plan.beamletMUs)
        return beamletDose

    def fromHU2Densities(self, ct : CTImage, overRidingList : Sequence[Dict[str, Any]] = None):
        """
        Convert the HU values of the CT image to densities using the calibration curve. It also override the density values of the CT image using the overRidingList

        Parameters
        ----------
        ct: CTImage
            Treatment planning CT image
        overRidingList: Sequence[Dict[str, Any]]
            It stores in every element of the sequence a dictionary with the keys 'Mask' and 'Value'. 'Mask' is the ROI mask and 'Value' is the value to override.
        """
        Density = self._ctCalibration._PiecewiseHU2Density__densities
        HU = self._ctCalibration._PiecewiseHU2Density__hu
        ct.imageArray = np.interp(ct.imageArray, HU, Density)
        if overRidingList is not None:
            for overRidingDict in overRidingList:
                ct.imageArray[overRidingDict['Mask'].imageArray.astype(bool) == True] = overRidingDict['Value']
        return ct


    def computeBeamlets(self, ct: CTImage, plan: PhotonPlan, roi: Sequence[Union[ROIContour, ROIMask]] = None, overRidingList: Sequence[Dict[str, Any]] = None) -> SparseBeamlets:
        """
        Compute beamlets using Collapse Cone Convolution algorithm

        Parameters
        ----------
        ct: CTImage
            Treatment planning CT image
        plan : PhotonPlan
            RT plan
        overRidingList: Sequence[Dict[str, Any]]
            It stores in every element of the sequence a dictionary with the keys 'Mask' and 'Value'. 'Mask' is the ROI mask and 'Value' is the value to override.
        Returns
        -------
        beamletDose:SparseBeamlets
            Beamlets dose with same grid size and spacing as the CT image

        """
        logger.info("Prepare Collapse Cone Convolution Beamlet calculation")
        if self._ct == None:
            self._ct = ct
            self._ct = self.fromHU2Densities(self._ct, overRidingList) 
            self._plan = plan

        if roi :
            roi = [roi] if not isinstance(roi, list) else roi
            self._roi = []
            for contour in roi:
                if isinstance(contour, ROIContour):
                    mask = contour.getBinaryMask(self._ct.origin, self._ct.gridSize, self._ct.spacing)
                else:
                    mask = contour
                self._roi.append(mask)

        self._cleanDir(self.outputDir)
        self._cleanDir(self._executableDir)
        self._cleanDir(self._beamDirectory)
        self._writeFilesToSimuDir()
        self.writeExecuteCCCfile()
        self._startCCC()

        beamletDose = self._importBeamlets()

        nbOfBeamlets = beamletDose._sparseBeamlets.shape[1]
        assert(nbOfBeamlets==len(self._plan.beamlets))
        beamletDose.beamletAngles_rad = self._plan.beamletsAngle_rad

        beamletsMU = np.array(plan.beamletMUs)
        if beamletDose.shape[1] != len(beamletsMU):
            print('ERROR: The beamlets imported from the dose engine don\'t have the same number as the beamlets in the plan')
            return
        if plan.planDesign.beamlets is not None and plan.planDesign.beamlets._weights is not None:
            beamletDose._weights = plan.planDesign.beamlets._weights
        else:
            beamletDose._weights = beamletsMU

        return beamletDose


    def computeRobustScenarioBeamlets(self, ct: CTImage, plan: PhotonPlan, roi: Sequence[Union[ROIContour, ROIMask]] = None, overRidingList: Sequence[Dict[str, Any]] = None, robustMode = "Shift", computeNominal = True, storePath:Optional[str] = None) -> SparseBeamlets:
        """
        Compute beamlets for different scenarios using Collapse Cone Convolution algorithm. The beamlets are saved in plan.planDesign.robustness

        Parameters
        ----------
        ct: CTImage
            Treatment planning CT image
        plan : PhotonPlan
            RT plan
        overRidingList: Sequence[Dict[str, Any]]
            It stores in every element of the sequence a dictionary with the keys 'Mask' and 'Value'. 'Mask' is the ROI mask and 'Value' is the value to override.
        robustMode: str ['Shift', 'Simulation']
            It selects the type of robust scenarios to calculate. 'Shift' calculates the scenarios by shifting the beamlets, 
            'Simulation' calculates the scenarios by simulating the beamlets again per every scenario.
        computeNominal: bool
            If true, the nominal scenario is calculated and stored in plan.planDesign.robustness.nominal.sb
        """
        logger.info("Prepare Collapse Cone Convolution Beamlet calculation")
        self._plan = plan
        self._ct = self.fromHU2Densities(ct, overRidingList) 
        self._roi = roi
        self._overRidingList = overRidingList
        self.batchSize = plan.numberOfBeamlets if plan.numberOfBeamlets / self.batchSize < 1 else self.batchSize
        origin = ct.origin

        plan.planDesign.robustness.generateRobustScenarios()
        scenarios = plan.planDesign.robustness.scenariosConfig

        if computeNominal:
            logger.info('Calculating Nominal Scenario')
            self.ROFolder = 'Nominal'
            nominal = self.computeBeamlets(self._ct, self._plan, overRidingList=overRidingList)   
            if not (storePath is None):
                outputBeamletFile = os.path.join(storePath, "BeamletMatrix_" + plan.seriesInstanceUID + "_Nominal.blm")
                nominal.storeOnFS(outputBeamletFile)
        else:
            plan.planDesign.robustness.nominal = plan.planDesign.beamlets 
            
        scenariosDoses = []
        for s, scenario in enumerate(scenarios):
            logger.info('Calculating Scenario {}'.format(s+1))
            logger.info(scenario)
            self.ROFolder = 'Scenario_{}'.format(s)
            scenario = self.calculateRobustBeamlets(scenario, origin, nominal, mode = robustMode)
            if not (storePath is None):
                outputBeamletFile = os.path.join(storePath,
                                                    "BeamletMatrix_" + plan.seriesInstanceUID + "_Scenario_" + str(
                                                        s + 1) + "-" + str(self._plan.planDesign.robustness.numScenarios) + ".blm")
                scenario.storeOnFS(outputBeamletFile)
            scenariosDoses.append(scenario)
        self._ct.origin = origin

        return nominal, scenariosDoses

    def calculateRobustBeamlets(self, scenario: RobustScenario, origin: Sequence[float], nominal:SparseBeamlets = None, mode = "Simulation"):
        """
        Compute the beamlets for a given scenario

        Parameters
        ----------
        scenario: RobustScenario
            scenario to calculate the beamlets
        origin : Sequence[float]
            origin of the treatment planning CT image
        nominal: SparseBeamlets
            nominal beamlets
        mode: str ['Shift', 'Simulation']
            It selects the type of robust scenarios to calculate. 'Shift' calculates the scenarios by shifting the beamlets, 
            'Simulation' calculates the scenarios by simulating the beamlets again per every scenario.
        Returns
        -------
        beamletsScenario:SparseBeamlets
            Beamlets dose with same grid size and spacing as the CT image
        """
        t0 = time.time()
        self._ct.origin = origin + scenario.sse
        scenario.sre = None if scenario.sre == [0,0,0] else scenario.sre 

        if mode == "Simulation":
            beamletsScenario = self.computeBeamlets(self._ct, self._plan, self._overRidingList, self._roi)
            beamletsScenario.doseOrigin = origin
        elif mode == "Shift" or scenario.sre != None:
            scenarioShift_voxel = scenario.sse / self._ct.spacing
            BeamletMatrix = []
            if nominal == None:
                KeyError('To calculate the robust scenarios beamlets in precise mode it is necessary the nominal beamlets')

            nbOfBeamlets = nominal._sparseBeamlets.shape[1]
            assert(nbOfBeamlets==len(self._plan.beamlets))

            BeamletMatrix = shiftBeamlets(nominal._sparseBeamlets, nominal.doseGridSize, scenarioShift_voxel, self._plan.beamletsAngle_rad) ### Implement the convolutions in case of sre in GPU look at shiftBeamlets
            beamletsScenario = SparseBeamlets()
            beamletsScenario.setUnitaryBeamlets(BeamletMatrix)
            beamletsScenario.doseOrigin = nominal.doseOrigin
            beamletsScenario.doseSpacing = nominal.doseSpacing
            beamletsScenario.doseGridSize = nominal.doseGridSize
            beamletsScenario._weights = nominal._weights
        else:
            KeyError('The only modes available to calculate the setup scenarios are "Simulation" or "Shift"')
        logger.info('The scenario runned in {:.2f}'.format(time.time()-t0))
        return beamletsScenario
    
    def computeRobustScenario(self, ct: CTImage, plan: PhotonPlan, roi: Optional[Sequence[Union[ROIContour, ROIMask]]] = None, overRidingList: Sequence[Dict[str, Any]] = None, robustMode = "Shift", computeNominal = True):
        """
        Compute robustness scenario using Collapse Cone Convolution

        Parameters
        ----------
        ct: CTImage
            Treatment planning CT image
        plan : PhotonPlan
            RT plan
        overRidingList: Sequence[Dict[str, Any]]
            It stores in every element of the sequence a dictionary with the keys 'Mask' and 'Value'. 'Mask' is the ROI mask and 'Value' is the value to override.
        robustMode: str ['Shift', 'Simulation']
            It selects the type of robust scenarios to calculate. 'Shift' calculates the scenarios by shifting the beamlets, 
            'Simulation' calculates the scenarios by simulating the beamlets again per every scenario.
        computeNominal: bool
            If true, the nominal scenario is calculated and stored in plan.planDesign.robustnessEval.nominal
        Returns
        -------
        scenarios:Robustness
            Robustness with nominal and error scenarios
        """
        logger.info("Prepare CCC Dose calculation")
        robustEval = plan.planDesign.robustnessEval
        self._ct = self.fromHU2Densities(ct, overRidingList)
        self._plan = plan
        self._roi = roi
        # CCC config
        self.batchSize = plan.numberOfBeamlets if plan.numberOfBeamlets / self.batchSize < 1 else self.batchSize
        origin = ct.origin
        plan.planDesign.robustnessEval.generateRobustScenarios()
        scenarios = plan.planDesign.robustnessEval.scenariosConfig
        
        if computeNominal:
            logger.info("Simulation of nominal scenario")
            self.ROFolder = 'Nominal'
            nominalBL = self.computeBeamlets(self._ct, self._plan)
            robustEval.setNominal(nominalBL.toDoseImage(), roi)
        
        logger.info("Simulation of error scenarios")
        for number, scenario in enumerate(scenarios):
            logger.info('Calculating Scenario {}'.format(number))
            logger.info(scenario)
            self.ROFolder = 'Scenario_{}'.format(number)
            dose = self.computeRobustScenarioDose(scenario, nominalBL, origin, mode = robustMode)
            robustEval.addScenario(dose, number, roi)
            self._ct.origin = origin

        return robustEval

    def computeDose(self, ct: CTImage, plan: PhotonPlan, overRidingList: Sequence[Dict[str, Any]] = None,  Density = False) -> DoseImage:
        """
        Compute dose distribution in the patient using Collapse Cone Convolution algorithm

        Parameters
        ----------
        ct : CTImage
            Treatment planning CT image of the patient
        plan : IonPlan
            RT plan
        overRidingList: Sequence[Dict[str, Any]]
            It stores in every element of the sequence a dictionary with the keys 'Mask' and 'Value'. 'Mask' is the ROI mask and 'Value' is the value to override.

        Returns
        -------
        DoseImage
            Dose distribution with same grid size and spacing as the CT image
        """ 
        logger.info("Prepare Collapse Cone Convolution Beamlet calculation")
        self._ct = ct
        self._plan = plan

        self._cleanDir(self.outputDir)
        self._cleanDir(self._executableDir)
        self._cleanDir(self._beamDirectory)
        if not Density:
            self._ct = self.fromHU2Densities(self._ct, overRidingList=overRidingList) 
        self._writeFilesToSimuDir()
        self.writeExecuteCCCfile()
        self._startCCC()


        Dose = self._importDose()
        Dose.imageArray *= self._plan.numberOfFractionsPlanned
        return Dose
  
    def computeRobustScenarioDose(self, scenario, nominal, origin, mode = "Simulation", overRidingList: Sequence[Dict[str, Any]] = None):
        """
        Compute the dose array for a given scenario

        Parameters
        ----------
        scenario: RobustScenario
            scenario to calculate the dose
        origin : Sequence[float]
            origin of the treatment planning CT image
        mode: str ['Shift', 'Simulation']
            It selects the type of robust scenarios to calculate. 'Shift' calculates the scenarios by shifting the beamlets, 
            'Simulation' calculates the scenarios by simulating the beamlets again per every scenario.
        Returns
        -------
        beamletsScenario:SparseBeamlets
            Dose with same grid size and spacing as the CT image
        """
        t0 = time.time()
        self._ct.origin = origin
 
        scenario.sre = None if np.all(scenario.sre == [0,0,0]) else scenario.sre

        if mode == "Simulation":
            self._ct.origin =+ scenario.sse
            logger.info(f"CT origin shifted from {origin} to {self._ct.origin}")
            DoseScenario = self.computeDose(self._ct, self._plan, overRidingList, Density = True)
            DoseScenario.origin = origin
            if np.all(scenario.sre) != None:
                DoseScenario.imageArray = gaussian_filter(DoseScenario.imageArray.astype(float), sigma = scenario.sre, order=0, truncate=2)

        elif mode == "Shift":
            nominal.doseSpacing = self._ct.spacing
            nbOfBeamlets = nominal._sparseBeamlets.shape[1]
            assert(nbOfBeamlets==len(self._plan.beamlets))
            DoseScenario = adjustDoseToScenario(scenario, nominal, self._plan)

        else:
            KeyError('The only modes available to calculate the setup scenarios are "Simulation" or "Shift"')
        logger.info('The scenario runned in {}'.format(time.time()-t0))
        return DoseScenario
