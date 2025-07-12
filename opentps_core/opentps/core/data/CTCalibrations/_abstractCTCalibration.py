
__all__ = ['AbstractCTCalibration']


from abc import abstractmethod


class AbstractCTCalibration:
    """
    Abstract class for CT calibration. Methods are redefined in mcSquareCTCalibration and rayStationCTCalibration.
    """
    @abstractmethod
    def convertHU2MassDensity(self, hu):
        pass

    @abstractmethod
    def convertHU2RSP(self, hu, energy):
        pass

    @abstractmethod
    def convertMassDensity2HU(self, density):
        pass

    @abstractmethod
    def convertMassDensity2RSP(self, density, energy):
        pass

    @abstractmethod
    def convertRSP2HU(self, rsp):
        pass

    @abstractmethod
    def convertRSP2MassDensity(self, rsp):
        pass