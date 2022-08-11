import configparser
import os

from programSettings import Singleton, ProgramSettings
from pathlib import Path

import config as configModule

class PlanOptimizationSettings(metaclass=Singleton):
    def __init__(self):
        programSettings = ProgramSettings()

        self._config_dir = programSettings.workspace
        self.configFile = os.path.join(self._config_dir, "planOptimizationSettings.cfg")

        if not Path(self.configFile).exists():
            with open(self.configFile, 'w') as file:
                self._defaultConfig.write(file)

            self._config = configparser.ConfigParser()
            self._config.read(self.configFile)
            self.workspace = str(Path.home() / "openTPS_workspace")  # Will also write config

        self._config = configparser.ConfigParser()
        self._config.read(self.configFile)

    def _createFolderIfNotExists(self, folder):
        folder = Path(folder)

        if not folder.is_dir():
            os.mkdir(folder)

    @property
    def _defaultConfig(self):
        configTemplate = configparser.ConfigParser()
        configTemplate.read(Path(str(configModule.__path__[0])) / "planOptimizationConfig_template.cfg")

        return configTemplate

    @property
    def beamletPrimaries(self) -> int:
        try:
            output = self._config["MCsquare"]["beamletPrimaries"]
            if not (output is None):
                return int(output)
        except:
            pass

        self._config["MCsquare"].update({"beamletPrimaries": str(1e5)})
        self.writeConfig()
        return int(self._config["MCsquare"]["MCsquare"])

    @beamletPrimaries.setter
    def beamletPrimaries(self, primaries:int):
        self._config["MCsquare"]["beamletPrimaries"] = str(primaries)

        self.writeConfig()

    @property
    def finalDosePrimaries(self) -> int:
        try:
            output = self._config["MCsquare"]["finalDosePrimaries"]
            if not (output is None):
                return int(output)
        except:
            pass

        self._config["MCsquare"].update({"finalDosePrimaries": str(1e8)})
        self.writeConfig()
        return int(self._config["MCsquare"]["MCsquare"])

    @beamletPrimaries.setter
    def beamletPrimaries(self, primaries: int):
        self._config["MCsquare"]["finalDosePrimaries"] = str(primaries)

    def writeConfig(self):
        with open(self.configFile, 'w') as file:
            self._config.write(file)

if __name__ == "__main__":
    PlanOptimizationSettings()