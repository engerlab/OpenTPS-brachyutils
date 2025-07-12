
__all__ = ['RayStationCTCalibration']


import numpy as np
from scipy.interpolate import interpolate

from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareCTCalibration import MCsquareCTCalibration
from opentps.core.data.CTCalibrations.RayStationCalibration._rayStationDensity2Material import RayStationDensity2Material
from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.CTCalibrations._piecewiseHU2Density import PiecewiseHU2Density


class RayStationCTCalibration(AbstractCTCalibration, PiecewiseHU2Density, RayStationDensity2Material):
    """
    Class for RayStation CT calibration. Inherits from AbstractCTCalibration, PiecewiseHU2Density and RayStationDensity2Material.
    """
    def __init__(self, piecewiseTable=(None, None), densities=None, materials=None, fromFiles=(None, None)):
        PiecewiseHU2Density.__init__(self, piecewiseTable=piecewiseTable, fromFile=fromFiles[0])
        RayStationDensity2Material.__init__(self, densities=densities, materials=materials, fromFile=fromFiles[1])

    def convertHU2MassDensity(self, hu):
        """
        Convert HU to mass density.

        Parameters
        ----------
        hu : float or array_like
            The HU value(s).

        Returns
        -------
        float or array_like
            The mass density value(s).
        """
        return PiecewiseHU2Density.convertHU2MassDensity(self, hu)

    def convertHU2RSP(self, hu, energy=100):
        """
        Convert HU to relative stopping power.

        Parameters
        ----------
        hu : float or array_like
            The HU value(s).
        energy : float (default=100)
            The energy of the beam in MeV.

        Returns
        -------
        float or array_like
            The relative stopping power value(s).
        """
        density = self.convertHU2MassDensity(hu)
        return self.convertMassDensity2RSP(density, energy)

    def convertMassDensity2HU(self, density):
        """
        Convert mass density to HU.

        Parameters
        ----------
        density : float or array_like
            The mass density value(s).

        Returns
        -------
        float or array_like
            The HU value(s).
        """
        return PiecewiseHU2Density.convertMassDensity2HU(self, density)

    def convertMassDensity2RSP(self, density, energy=100):
        """
        Convert mass density to relative stopping power.

        Parameters
        ----------
        density : float or array_like
            The mass density value(s).
        energy : float (default=100)
            The energy of the beam in MeV.

        Returns
        -------
        float or array_like
            The relative stopping power value(s).
        """
        return RayStationDensity2Material.convertMassDensity2RSP(self, density, energy)

    def convertRSP2HU(self, rsp, energy=100):
        """
        Convert relative stopping power to HU.

        Parameters
        ----------
        rsp : float or array_like
            The relative stopping power value(s).
        energy : float (default=100)
            The energy of the beam in MeV.

        Returns
        -------
        float or array_like
            The HU value(s).
        """
        return self.convertMassDensity2HU(self.convertRSP2MassDensity(rsp, energy))

    def convertRSP2MassDensity(self, rsp, energy=100):
        """
        Convert relative stopping power to mass density.

        Parameters
        ----------
        rsp : float or array_like
            The relative stopping power value(s).
        energy : float (default=100)
            The energy of the beam in MeV.

        Returns
        -------
        float or array_like
            The mass density value(s).
        """
        return RayStationDensity2Material.convertRSP2MassDensity(self, rsp, energy)

    def toMCSquareCTCalibration(self, materialsPath='default'):
        """
        Convert RayStation CT calibration to MCsquare CT calibration.

        Returns
        -------
        MCsquareCTCalibration
            The MCsquare CT calibration.
        """
        hu, densities = self.getPiecewiseHU2MassDensityConversion()
        densities = np.array(densities)
        hu = np.array(hu)

        mcsMaterials = [material.toMCSquareMaterial() for material in self._materials]
        mcsDensities = [material.density for material in self._materials]
        mcsDensities = np.array(mcsDensities)

        fDensity2HU = interpolate.interp1d(np.insert(densities, 0, 0), np.insert(hu, 0, hu[0]), kind='linear', fill_value='extrapolate')

        densityMid = mcsDensities[0:-2] + (mcsDensities[1:-1] - mcsDensities[0:-2]) / 2.0
        huMid = fDensity2HU(densityMid)
        huMid = np.insert(huMid, 0, hu[0])
        huMid = np.array(huMid)

        flipInd = np.arange(len(huMid)-1, -1, -1)
        flipInd = flipInd.astype('int')
        huMid = huMid[flipInd]
        huMid, ind = np.unique(huMid, return_index=True)  # Take last element and not first when repetitive elements
        huMidInd = flipInd[ind]

        mcsMaterials = [mcsMaterials[i] for i in huMidInd]
        hu2materials = (huMid, mcsMaterials)

        # Set material number
        maxElementNb = 0
        for material in mcsMaterials:
            elements = material.MCsquareElements
            m = np.array([element.number for element in elements]).max()

            if m > maxElementNb:
                maxElementNb = m

        for i, material in enumerate(mcsMaterials):
            material.number = maxElementNb+i+1

        return MCsquareCTCalibration(hu2densityTable=(hu, densities), hu2materialTable=hu2materials)



#test
if __name__ == '__main__':
    calibration = RayStationCTCalibration(fromFiles=('/home/sylvain/Documents/openReggui/flashTPS/parameters/calibration_trento_cef.txt',
                                       '/home/sylvain/Documents/openReggui/flashTPS/parameters/materials_cef.txt'))

    print(calibration.convertHU2MassDensity(-1024))
    print(calibration.convertHU2MassDensity(0))

    print(calibration.convertMassDensity2HU(calibration.convertHU2MassDensity(0)))
    print(calibration.convertRSP2HU(calibration.convertHU2RSP([1000, 100])))

    print(calibration.convertHU2RSP([-1000, 0, 3000], 100))

    mc2Calib = calibration.toMCSquareCTCalibration()

    print(mc2Calib)

    mc2Calib.write('/home/sylvain/Documents/sandbox', 'scanner')
    exit()