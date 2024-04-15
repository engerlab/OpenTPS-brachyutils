
__all__ = ['MCsquareCTCalibration']

from typing import Optional
import os

import numpy as np
from scipy.interpolate import interpolate

from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareHU2Material import MCsquareHU2Material
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMolecule import MCsquareMolecule
from opentps.core.data.CTCalibrations._abstractCTCalibration import AbstractCTCalibration
from opentps.core.data.CTCalibrations._piecewiseHU2Density import PiecewiseHU2Density


class MCsquareCTCalibration(AbstractCTCalibration, PiecewiseHU2Density, MCsquareHU2Material):
    """
    Class for the CT calibration for MCsquare. Inherits from AbstractCTCalibration, PiecewiseHU2Density and MCsquareHU2Material.
    """
    def __init__(self, hu2densityTable=([], []), hu2materialTable=([], []), fromFiles=(None, None, 'default')):
        PiecewiseHU2Density.__init__(self, piecewiseTable=hu2densityTable, fromFile=fromFiles[0])
        MCsquareHU2Material.__init__(self, piecewiseTable=hu2materialTable, fromFile=(fromFiles[1], fromFiles[2]))

    def __str__(self):
        s = 'HU - Density\n'
        s += PiecewiseHU2Density.__str__(self)
        s += 'HU - Material\n'
        s += MCsquareHU2Material.__str__(self)

        return s

    @classmethod
    def fromFiles(cls, huDensityFile, huMaterialFile, materialsPath='default'):
        """
        Create a MCsquareCTCalibration object from files.

        Parameters
        ----------
        huDensityFile : str
            Path to the file containing the HU to mass density conversion table.
        huMaterialFile : str
            Path to the file containing the HU to material conversion table.
        materialsPath : str (optional, default='default')
            Path to the folder containing the material files. Default is 'default' which means that the default materials folder of MCsquare will be used.

        Returns
        -------
        MCsquareCTCalibration
            The MCsquareCTCalibration object.
        """
        newObj = cls()

        newObj._initializeFromFile(huDensityFile)
        newObj._initializeFromFiles(huMaterialFile, materialsPath=materialsPath)

        return newObj

    def addEntry(self, hu:float=None, density:Optional[float]=None, material:Optional[MCsquareMolecule]=None):
        """
        Add an entry to the HU to mass density and HU to material conversion tables. Either density or material must be None, and the other must be a valid value.

        Parameters
        ----------
        hu : float
            The HU value.
        density : float (optional)
            The mass density value.
        material : MCsquareMolecule (optional)
            The material.
        """
        if not (density is None) and not(hu is None):
            PiecewiseHU2Density.addEntry(self, hu, density)
        if not(material is None) and not(hu is None):
            MCsquareHU2Material.addEntry(self, hu, material)
    
        if hu is None:
            assert material is not None
            if len(self.allMaterialsAndElements()) < 2:
                raise ValueError(f"Need at least two elements in HU to density table to infer HU value of material {material.name}")
            self.addEntry(hu=self.convertMassDensity2HU(material.density), density=material.density, material=material)
                

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
            The energy of the proton beam in MeV.

        Returns
        -------
        float or array_like
            The relative stopping power value(s).
        """
        densities = self.convertHU2MassDensity(hu)
        return densities*self.convertHU2SP(hu, energy=energy)/self.waterSP(energy=energy)

    def waterSP(self, energy:float=100.) -> float:
        """
        Get the stopping power of water at a given energy.

        Parameters
        ----------
        energy : float (default=100)
            The energy of the proton beam in MeV.

        Returns
        -------
        float
            The stopping power of water at the given energy.
        """
        material = MCsquareMolecule.load(17, 'default') # 17 is the ID of Water. This is hard-coded in MCsquare
        return material.stoppingPower(energy)

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
            The energy of the proton beam in MeV.

        Returns
        -------
        float or array_like
            The relative stopping power value(s).
        """
        return self.convertHU2RSP(self.convertMassDensity2HU(density), energy=energy)

    def convertRSP2HU(self, rsp, energy=100):
        """
        Convert relative stopping power to HU.

        Parameters
        ----------
        rsp : float or array_like
            The relative stopping power value(s).
        energy : float (default=100)
            The energy of the proton beam in MeV.

        Returns
        -------
        float or array_like
            The HU value(s).
        """
        hu_ref, _ = self.getPiecewiseHU2MassDensityConversion()
        rsp_ref = self.convertHU2RSP(hu_ref, energy)

        density = interpolate.interp1d(rsp_ref, hu_ref, kind='linear', fill_value='extrapolate')

        return density(rsp)
    
    def convertMaterial2HU(self, materialID):
        return MCsquareHU2Material.convertMaterial2HU(self, materialID)

    def _getBijectiveHU2RSP(self, HuMin=-1100., huMax=5000., step=2., energy=100):
        hu_ref = np.arange(HuMin, huMax+step, step)
        rsp_ref = self.convertHU2RSP(hu_ref, energy)
        rsp_ref = np.array(rsp_ref)

        while not np.all(np.diff(rsp_ref) >= 0):
            rsp_diff = np.concatenate((np.array([1.0]), np.diff(rsp_ref)))

            rsp_ref = rsp_ref[rsp_diff > 0]
            hu_ref = hu_ref[rsp_diff > 0]

            rsp_ref, ind = np.unique(rsp_ref, return_index=True)
            hu_ref = hu_ref[ind]

        return (hu_ref, rsp_ref)

    def convertRSP2MassDensity(self, rsp, energy=100):
        """
        Convert relative stopping power to mass density.

        Parameters
        ----------
        rsp : float or array_like
            The relative stopping power value(s).
        energy : float (default=100)
            The energy of the proton beam in MeV.

        Returns
        -------
        float or array_like
            The mass density value(s).
        """
        return self.convertHU2MassDensity(self.convertRSP2HU(rsp, energy=energy))

    def write(self, scannerPath, materialPath):
        """
        Write the HU to mass density and HU to material conversion tables to files.

        Parameters
        ----------
        scannerPath : str
            Path to the folder to write the HU to mass density conversion table to.
        materialPath : str
            Path to the folder to write the HU to material conversion table to.
        """
        PiecewiseHU2Density.write(self, os.path.join(scannerPath, 'HU_Density_Conversion.txt'))
        MCsquareHU2Material.write(self, materialPath, os.path.join(scannerPath, 'HU_Material_Conversion.txt'))

    @classmethod
    def fromCTCalibration(cls, ctCalibration: AbstractCTCalibration):
        """
        Create a MCsquareCTCalibration object from a AbstractCTCalibration object (RayStationCalibration).

        Parameters
        ----------
        ctCalibration : AbstractCTCalibration
            The AbstractCTCalibration object.

        Returns
        -------
        MCsquareCTCalibration
            The MCsquareCTCalibration object.

        Raises
        ------
        NotImplementedError
            If the conversion is not implemented.
        """
        from opentps.core.data.CTCalibrations.RayStationCalibration._rayStationCTCalibration import RayStationCTCalibration

        if isinstance(ctCalibration, RayStationCTCalibration):
            return ctCalibration.toMCSquareCTCalibration()
        else:
            raise NotImplementedError('Conversion from ' + ctCalibration.__class__.__name__ + ' to ' + cls.__class__.__name__ + ' is not implemented.')

# test
if __name__ == '__main__':
    import os
    import opentps.core.processing.doseCalculation.MCsquare as MCsquareModule

    MCSquarePath = str(MCsquareModule.__path__[0])
    scannerPath = os.path.join(MCSquarePath, 'scanners', 'UCL_Toshiba')

    calibration = MCsquareCTCalibration(fromFiles=(os.path.join(scannerPath, 'HU_Density_Conversion.txt'),
                                                   os.path.join(scannerPath, 'HU_Material_Conversion.txt'),
                                                   os.path.join(MCSquarePath, 'Materials')))

    print(calibration)

    #calibration.write('/home/sylvain/Documents/sandbox', 'scanner')

    print(calibration.convertHU2RSP(-2000))
    print(calibration.convertHU2MassDensity(-2000))
    print(calibration.convertMassDensity2HU(calibration.convertHU2MassDensity(-2000)))
    print(calibration.convertRSP2HU(calibration.convertHU2RSP(-2000)))
    print(calibration.convertRSP2MassDensity(calibration.convertHU2RSP(-2000)))

    print(calibration.convertMassDensity2HU(8.3))
    print(calibration.convertMassDensity2RSP(1.5))