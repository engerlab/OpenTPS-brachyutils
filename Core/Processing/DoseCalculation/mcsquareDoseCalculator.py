import os
import platform
import shutil
from pathlib import Path
from typing import Optional

from Core.Data.CTCalibrations.abstractCTCalibration import AbstractCTCalibration
from Core.Data.Images.ctImage import CTImage
from Core.Data.Images.doseImage import DoseImage
from Core.Data.Images.roiMask import ROIMask
from Core.Data.MCsquare.bdl import BDL
from Core.Data.MCsquare.mcsquareConfig import MCsquareConfig
from Core.Data.Plan.rtPlan import RTPlan
from Core.Processing.DoseCalculation.abstractDoseInfluenceCalculator import AbstractDoseInfluenceCalculator
from Core.Processing.DoseCalculation.abstractMCDoseCalculator import AbstractMCDoseCalculator
from mainConfig import MainConfig

import Core.IO.mcsquareIO as mcsquareIO


class MCSquareDoseCalculator(AbstractMCDoseCalculator, AbstractDoseInfluenceCalculator):
    def __init__(self):
        AbstractMCDoseCalculator.__init__(self)
        AbstractDoseInfluenceCalculator.__init__(self)

        self._ctCalibration = None
        self._mcsquareCTCalibration = None
        self._beamModel = None
        self._nbPrimaries = 0
        self._simulationDirectory = MainConfig().simulationFolder

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
    def simulationDirectory(self) -> str:
        return str(self._simulationDirectory)

    @simulationDirectory.setter
    def simulationDirectory(self, path):
        self._simulationDirectory = path

    def computeDose(self, ct:CTImage, plan: RTPlan) -> DoseImage:
        self._ct = ct
        self._plan = plan

        self._cleanDir(self._materialFolder)
        self._cleanDir(self._scannerFolder)
        self._cleanDir(self._outputDir)
        self._writeFilesToSimuDir()
        self._startMCsquare()

        doseImage = self._importResults()

        return doseImage

    def computeDoseInfluence(self, ct:CTImage, plan: RTPlan, roi:Optional[ROIMask]=None):
        raise NotImplementedError()

    def _cleanDir(self, dirPath):
        if os.path.isdir(dirPath):
            shutil.rmtree(dirPath)

    def _writeFilesToSimuDir(self):
        mcsquareIO.writeCT(self._ct, self._ctFilePath)
        mcsquareIO.writePlan(self._plan, self._planFilePath, self._ct, self._beamModel)
        mcsquareIO.writeBDL(self._beamModel, self._bdlFilePath)
        mcsquareIO.writeCTCalibration(self._ctCalibration, self._scannerFolder, self._materialFolder)
        mcsquareIO.writeConfig(self._doseComputationConfig, self._configFilePath)
        mcsquareIO.writeBin(self._mcsquareSimuDir)

    def _startMCsquare(self):
        if (platform.system() == "Linux"):
            os.system("cd " + self._mcsquareSimuDir + " &&  sh MCsquare")
        elif (platform.system() == "Windows"):
            os.system("cd " + self._mcsquareSimuDir + " && MCsquare_win.bat")

    def _importResults(self) -> DoseImage:
        dose = mcsquareIO.readDose(self._doseFilePath)
        dose.patient = self._ct.patient

        dose.imageArray = dose.imageArray * self._deliveredProtons() * 1.602176e-19 * 1000

        return dose

    def _deliveredProtons(self) -> int:
        deliveredProtons = 0
        for beam in self._plan:
            for layer in beam:
                Protons_per_MU = self._beamModel.computeMU2Protons(layer.nominalEnergy)
                deliveredProtons += sum(layer.spotWeights) * Protons_per_MU

        return deliveredProtons

    @property
    def _mcsquareSimuDir(self):
        folder =  os.path.join(self._simulationDirectory, 'MCsquare_simulation')
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def _outputDir(self):
        folder =  os.path.join(self._mcsquareSimuDir, 'Outputs')
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
    def _doseComputationConfig(self) -> MCsquareConfig:
        config = self._generalMCsquareConfig

        config["Dose_to_Water_conversion"] = "OnlineSPR"

        return config

    @property
    def _generalMCsquareConfig(self) -> MCsquareConfig:
        config = MCsquareConfig()

        config["WorkDir"] = self._mcsquareSimuDir
        config["CT_File"] = self._ctName
        config["ScannerDirectory"] = self._scannerFolder # ??? Required???
        config["HU_Density_Conversion_File"] = os.path.join(self._scannerFolder, "HU_Density_Conversion.txt")
        config["HU_Material_Conversion_File"] = os.path.join(self._scannerFolder, "HU_Material_Conversion.txt")
        config["BDL_Machine_Parameter_File"] = self._bdlFilePath
        config["BDL_Plan_File"] = self._planFilePath

        return config

    def _createFolderIfNotExists(self, folder):
        folder = Path(folder)

        if not folder.is_dir():
            os.mkdir(folder)
