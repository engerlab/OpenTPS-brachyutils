
import logging

from opentps.core.utils.applicationConfig import AbstractApplicationConfig


logger = logging.getLogger(__name__)


class ScanAlgoSimulationConfig(AbstractApplicationConfig):
    """
    This class is used to read and write the configuration of the scan algorithm simulation.

    Attributes
    ----------
    gantry : str
        The type of gantry used for the simulation.
    gateway : str
        The IP address of the gateway used for the simulation.
    """
    def __init__(self):
        super().__init__()

        self._writeAllFieldsIfNotAlready()

    def _writeAllFieldsIfNotAlready(self):
        self.gantry
        self.gateway

    @property
    def gantry(self) -> str:
        return self.getConfigField("DeliverySimulation", "Gantry", "gantry type")

    @gantry.setter
    def gantry(self, gantry_type:str):
        self.setConfigField("DeliverySimulation", "Gantry", gantry_type)

    @property
    def gateway(self) -> str:
        return self.getConfigField("DeliverySimulation", "Gateway", "127.0.0.1")

    @gateway.setter
    def gateway(self, IP: str):
        self.setConfigField("DeliverySimulation", "Gateway", IP)