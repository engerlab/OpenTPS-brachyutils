import configparser
import os

from os import mkdir, makedirs
from pathlib import Path

from pip._internal.utils import appdirs

import opentps.core.config as configModule
import opentps.core.config.logger as loggingModule


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class ProgramSettings(metaclass=Singleton):
    """
    This class is a singleton and should be used to get the program settings.

    The program settings are stored in a config file in the user's config directory.

    The config file is created if it does not exist.

    Attributes
    ----------
    programSettingsFolder : str
        The folder where the program settings are stored.
    workspace : str
        The folder where the workspace is located.
    startScriptFolder : str
        The folder where the start scripts are located.
    simulationFolder : str
        The folder where the simulations are located.
    loggingConfigFile : str
        The path to the logging config file.
    resultFolder : str
        The folder where the results are located.
    logFolder : str
        The folder where the logs are located.
    exampleFolder : str
        The folder where the examples are located.
    """
    def __init__(self):
        self._config_dir = Path(appdirs.user_config_dir("openTPS"))
        self._configFile = self._config_dir / "mainConfig.cfg"
        self._loggingConfigFilePath = loggingModule.__path__[0] + os.sep + 'logging_config.json'

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
    def programSettingsFolder(self):
        return str(self._config_dir)

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
        self._config["dir"]["loggingConfigFile"] = str(self._loggingConfigFilePath)
        self._config["dir"]["exampleFolder"] = str(path / "examples")

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
    def loggingConfigFile(self):
        return self._loggingConfigFilePath

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

    def writeConfig(self):
        """
        Write the config to the config file.
        """
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

        return configTemplate

if __name__ == "__main__":
    ProgramSettings()