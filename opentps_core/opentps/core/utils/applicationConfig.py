
import configparser
import logging
import os
from typing import Any

from opentps.core.utils.programSettings import Singleton, ProgramSettings
from pathlib import Path

logger = logging.getLogger(__name__)

# Since this is a singleton AbstractApplicationConfig must be abstract if we want several ApplicationConfig to coexist
class AbstractApplicationConfig(metaclass=Singleton):
    """
    Abstract class for application configuration. This class is a singleton.

    Attributes
    ----------
    configFile : str
        Path to the configuration file.
    """
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
        """
        Get a configuration field from the configuration file. If the field does not exist, it will be created with the default value.

        Parameters
        ----------
        section : str
            Section of the configuration file.
        field : str
            Field of the configuration file.
        defaultValue : Any
            Default value of the field.

        Returns
        -------
        str
            Configuration of the field.
        """
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
        """
        Set a configuration field from the configuration file.

        Parameters
        ----------
        section : str
            Section of the configuration file.
        field : str
            Field of the configuration file.
        value : Any
            Value of the field.

        Returns
        -------
        str
            Configuration of the field.
        """
        try:
            self._config[section]
        except:
            self._config.add_section(section)

        self._config[section][field] = str(value)
        self.writeConfig()

    def writeConfig(self):
        """
        Write the configuration file.

        Returns
        -------
        str
            Configuration of the field.
        """
        with open(self.configFile, 'w') as file:
            self._config.write(file)
