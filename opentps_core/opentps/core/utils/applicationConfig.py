
import configparser
import logging
import os
from typing import Any

from opentps.core.utils.programSettings import Singleton, ProgramSettings
from pathlib import Path

logger = logging.getLogger(__name__)

# Since this is a singleton AbstractApplicationConfig must be abstract if we want several ApplicationConfig to coexist
class AbstractApplicationConfig(metaclass=Singleton):
    def __init__(self):
        programSettings = ProgramSettings()

        self._config_dir = os.path.join(programSettings.workspace, "Config")
        self.configFile = os.path.join(self._config_dir, self.__class__.__name__ + ".cfg")

        if not Path(self.configFile).exists():
            os.makedirs(self._config_dir, exist_ok=True)

            with open(self.configFile, 'w') as file:
                file.write("")

            self._config = configparser.ConfigParser()
            self._config.read(self.configFile)

        self._config = configparser.ConfigParser()
        self._config.read(self.configFile)

    def _createFolderIfNotExists(self, folder):
        folder = Path(folder)

        if not folder.is_dir():
            os.mkdir(folder)

    def getConfigField(self, section:str, field:str, defaultValue:Any) -> str:
        try:
            output = self._config[section][field]
            if not (output is None):
                return output
        except:
            pass

        try:
            self._config[section]
        except:
            self._config.add_section(section)

        self._config[section].update({field: str(defaultValue)})
        self.writeConfig()
        return self._config[section][field]

    def setConfigField(self, section:str, field:str, value:Any):
        try:
            self._config[section]
        except:
            self._config.add_section(section)

        self._config[section][field] = str(value)
        self.writeConfig()

    def writeConfig(self):
        with open(self.configFile, 'w') as file:
            self._config.write(file)
