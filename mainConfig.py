import configparser
from os import mkdir, makedirs
from pathlib import Path

from pip._internal.utils import appdirs

import config as configModule


class MainConfig:
    def __init__(self):
        self._config_dir = Path(appdirs.user_config_dir("openTPS"))
        self._configFile = self._config_dir / "mainConfig.cfg"

        if not self._configFile.exists():
            makedirs(self._config_dir, exist_ok=True)
            with open(self._configFile, 'w') as file:
                self._defaultConfig.write(file)

        self._config = configparser.ConfigParser()
        self._config.read(self._configFile)

    @property
    def workspace(self):
        return self._config["dir"]["workspace"]

    @workspace.setter
    def workspace(self, path):
        path = Path(path)

        self._checkFolder(path)

        self._config["dir"]["workspace"] = str(path)
        self._config["dir"]["startScriptFolder"] = str(path / "startScriptFolder")
        self._config["dir"]["resultFolder"] = str(path / "resultFolder")
        self._config["dir"]["logFolder"] = str(path / "logFolder")
        self._config["dir"]["exampleFolder"] = str(path / "exampleFolder")

        self.writeConfig()

    @property
    def startScriptFolder(self):
        folder = self._config["dir"]["startScriptFolder"]
        self._checkFolder(folder)
        return folder

    @property
    def resultFolder(self):
        folder = self._config["dir"]["resultFolder"]
        self._checkFolder(folder)
        return folder

    @property
    def logFolder(self):
        folder = self._config["dir"]["logFolder"]
        self._checkFolder(folder)
        return folder

    @property
    def exampleFolder(self):
        folder = self._config["dir"]["exampleFolder"]
        self._checkFolder(folder)
        return folder

    def writeConfig(self):
        with open(self._configFile, 'w') as file:
            self._config.write(file)

    def _checkFolder(self, folder):
        folder = Path(folder)
        
        if not folder.is_dir():
            mkdir(folder)

    @property
    def _defaultConfig(self):
        configTemplate = configparser.ConfigParser()
        configTemplate.read(Path(str(configModule.__path__[0])) / "config_template.cfg")

        configTemplate["dir"]["workspace"] = str(Path.home() / "openTPS_workspace")
        self._checkFolder(configTemplate["dir"]["workspace"])

        return configTemplate

if __name__ == "__main__":
    MainConfig()