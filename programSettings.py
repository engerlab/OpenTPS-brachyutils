import configparser
import os
from os import mkdir, makedirs
from pathlib import Path

from pip._internal.utils import appdirs

import config as configModule
import Core.Processing.DoseCalculation.MCsquare.Scanners as ScannerModule
import Core.Processing.DoseCalculation.MCsquare.BDL as bdlModule

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class ProgramSettings(metaclass=Singleton):
    def __init__(self):
        self._config_dir = Path(appdirs.user_config_dir("openTPS"))
        self._configFile = self._config_dir / "mainConfig.cfg"

        if not self._configFile.exists():
            makedirs(self._config_dir, exist_ok=True)
            with open(self._configFile, 'w') as file:
                self._defaultConfig.write(file)

            self._config = configparser.ConfigParser()
            self._config.read(self._configFile)
            self.workspace = str(Path.home() / "openTPS_workspace")  # Will also write config

        self._config = configparser.ConfigParser()
        self._config.read(self._configFile)

    @property
    def workspace(self):
        return self._config["dir"]["workspace"]

    @workspace.setter
    def workspace(self, path):
        path = Path(path)

        self._createFolderIfNotExists(path)

        self._config["dir"]["workspace"] = str(path)
        self._config["dir"]["startScriptFolder"] = str(path / "StartScripts")
        self._config["dir"]["resultFolder"] = str(path / "Results")
        self._config["dir"]["simulationFolder"] = str(path / "Simulations")
        self._config["dir"]["logFolder"] = str(path / "Logs")
        self._config["dir"]["exampleFolder"] = str(path / "Examples")

        self.writeConfig()

    @property
    def startScriptFolder(self):
        folder = self._config["dir"]["startScriptFolder"]
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def simulationFolder(self):
        folder = self._config["dir"]["simulationFolder"]
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def resultFolder(self):
        folder = self._config["dir"]["resultFolder"]
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def logFolder(self):
        folder = self._config["dir"]["logFolder"]
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def exampleFolder(self):
        folder = self._config["dir"]["exampleFolder"]
        self._createFolderIfNotExists(folder)
        return folder

    @property
    def scannerFolder(self):
        try:
            output = self._config["machine_param"]["scannerFolder"]
            if not (output is None):
                return output
        except:
            pass

        self._config["machine_param"].update({"scannerFolder": ScannerModule.__path__[0] + os.sep  + 'UCL_Toshiba'})
        self.writeConfig()
        return self._config["machine_param"]["scannerFolder"]

    @scannerFolder.setter
    def scannerFolder(self, path):
        self._config["machine_param"]["scannerFolder"] = path

        self.writeConfig()

    @property
    def bdlFile(self):
        try:
            output = self._config["machine_param"]["bdlFile"]
            if not (output is None):
                return output
        except:
            pass

        self._config["machine_param"].update({"bdlFile" : bdlModule.__path__[0] + os.sep  + 'UMCG_P1_v2_RangeShifter.txt'})
        self.writeConfig()
        return self._config["machine_param"]["bdlFile"]

    @bdlFile.setter
    def bdlFile(self, path):
        self._config["machine_param"]["bdlFile"] = path

        self.writeConfig()

    def writeConfig(self):
        with open(self._configFile, 'w') as file:
            self._config.write(file)

    def _createFolderIfNotExists(self, folder):
        folder = Path(folder)
        
        if not folder.is_dir():
            mkdir(folder)

    @property
    def _defaultConfig(self):
        configTemplate = configparser.ConfigParser()
        configTemplate.read(Path(str(configModule.__path__[0])) / "config_template.cfg")

        self._createFolderIfNotExists(configTemplate["dir"]["workspace"])

        return configTemplate

if __name__ == "__main__":
    ProgramSettings()