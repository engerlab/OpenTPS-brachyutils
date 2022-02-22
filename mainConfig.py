import configparser
from os import mkdir, makedirs
from pathlib import Path

from pip._internal.utils import appdirs

import config as configModule


class MainConfig:
    def __init__(self):
        self._workspace = Path.home() / "openTPS_workspace"

        config_dir = Path(appdirs.user_config_dir("openTPS"))
        configFile = config_dir / "mainConfig.cfg"

        if not configFile.exists():
            makedirs(config_dir, exist_ok=True)
            with open(configFile, 'w') as file:
                self._defaultConfig.write(file)

        self._config = configparser.ConfigParser()
        self._config.read(configFile)

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

    def _checkFolder(self, folder):
        if not self._workspace.is_dir():
            mkdir(folder)

    @property
    def _defaultConfig(self):
        configTemplate = configparser.ConfigParser()
        configTemplate.read(Path(str(configModule.__path__[0])) / "config_template.cfg")

        configTemplate["dir"]["startScriptFolder"] = str(self._workspace / configTemplate["dir"]["startScriptFolder"])
        configTemplate["dir"]["resultFolder"] = str(self._workspace / configTemplate["dir"]["resultFolder"])
        configTemplate["dir"]["logFolder"] = str(self._workspace / configTemplate["dir"]["logFolder"])
        configTemplate["dir"]["exampleFolder"] = str(self._workspace / configTemplate["dir"]["exampleFolder"])

        if not self._workspace.is_dir():
            mkdir(self._workspace)

        return configTemplate

if __name__ == "__main__":
    MainConfig()