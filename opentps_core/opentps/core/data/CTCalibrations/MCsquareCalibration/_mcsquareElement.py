import os
import re
import numpy as np

from opentps.core.data.CTCalibrations.MCsquareCalibration._G4StopPow import G4StopPow
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMaterial import MCsquareMaterial


class MCsquareElement(MCsquareMaterial):
    """
    Class for MCsquare elements. Inherits from MCsquareMaterial.

    Attributes
    ----------
    atomicWeight : float (default 0.0)
        Atomic weight of the element.
    """
    def __init__(self, density=0.0, electronDensity=0.0, name=None, number=0, sp=None, radiationLength=0.0, atomicWeight=0.0):
        super().__init__(density=density, electronDensity=electronDensity, name=name, number=number, sp=sp, radiationLength=radiationLength)

        self.atomicWeight = atomicWeight
        self._nuclear_data = ""
        self._nuclearElasticData = None
        self._nuclearInelasticData = None
        self._promptGamma = None

    def __str__(self):
        return self.mcsquareFormatted()

    def mcsquareFormatted(self, materialNamesOrderedForPrinting=None):
        """
        Get element data in MCsquare format.

        Returns
        -------
        s : str
            Element data in MCsquare format.
        """
        if self.density<=0:
            self.density = 1e-18

        if self.electronDensity<=0:
            self.electronDensity = 1e-18

        s = 'Name ' + self.name + '\n'
        s += 'Atomic_Weight ' + str(self.atomicWeight) + '\n'
        s += 'Density ' + str(self.density) + " # in g/cm3 \n"
        s += 'Electron_Density ' + str(self.electronDensity) + " # in cm-3 \n"
        s += 'Radiation_Length ' + str(self.radiationLength) + " # in g/cm2 \n"
        s += 'Nuclear_Data ' + self._nuclear_data + '\n'

        return s

    @classmethod
    def load(cls, materialNb, materialsPath='default'):
        """
        Load element from file.

        Parameters
        ----------
        materialNb : int
            Number of the material.
        materialsPath : str (default 'default')
            Path to materials folder. If 'default', the default path is used.

        Returns
        -------
        self : MCsquareElement
            The loaded element.
        """
        elementPath = MCsquareMaterial.getFolderFromMaterialNumber(materialNb, materialsPath)

        self = cls()

        self.number = materialNb
        self.MCsquareElements = []
        self.weights = []

        with open(os.path.join(elementPath, 'Material_Properties.dat'), "r") as f:
            for line in f:
                if re.search(r'Name', line):
                    line = line.split()
                    self.name = line[1]
                    continue

                if re.search(r'Atomic_Weight', line):
                    line = line.split()
                    self.atomicWeight = float(line[1])
                    continue

                if re.search(r'Electron_Density', line):
                    line = line.split()
                    self.electronDensity = float(line[1])
                    continue
                elif re.search(r'Density', line):
                    line = line.split()
                    self.density = float(line[1])
                    continue

                if re.search(r'Radiation_Length', line):
                    line = line.split()
                    self.radiationLength = float(line[1])
                    continue

                if re.search(r'Nuclear_Data', line):
                    if 'ICRU' in line:
                        self._nuclear_data = 'ICRU'

                        file = open(os.path.join(elementPath, 'ICRU_Nuclear_elastic.dat'), mode='r',encoding="utf-8")
                        self._nuclearElasticData = file.read()
                        file.close()

                        file = open(os.path.join(elementPath, 'ICRU_Nuclear_inelastic.dat'), mode='r',encoding="utf-8")
                        self._nuclearInelasticData = file.read()
                        file.close()

                        file = open(os.path.join(elementPath, 'ICRU_PromptGamma.dat'), mode='r')
                        self._promptGamma = file.read()
                        file.close()
                    else:
                        self._nuclear_data = 'proton-proton'

                if re.search(r'Mixture_Component', line):
                    raise ValueError(elementPath + ' is a molecule not an element.')

        self.sp = G4StopPow(fromFile=os.path.join(elementPath, 'G4_Stop_Pow.dat'))
        self.pstarSP = None
        if os.path.exists(os.path.join(elementPath, 'PSTAR_Stop_Pow.dat')):
            self.pstarSP = G4StopPow(fromFile=os.path.join(elementPath, 'PSTAR_Stop_Pow.dat'))

        return self
    
    def stoppingPower(self, energy:float=100.) -> float:
        """
        Get stopping power of the material.

        Parameters
        ----------
        energy : float (default 100.)
            Energy in MeV.

        Returns
        -------
        s : float
            Stopping power in MeV cm2/g at the given energy.
        """
        e, s = self.sp.toList()
        return np.interp(energy, e, s)

    @property
    def rsp(self):
        waterSP = 7.25628392 # water (element 17 in default table) SP at 100MeV: ctCalibration.waterSP(energy=100)
        return self.density * self.stoppingPower(energy=100)/waterSP

    def write(self, folderPath, materialNamesOrderedForPrinting):
        """
        Write element data in specified folder.

        Parameters
        ----------
        folderPath : str
            Folder path.
        materialNamesOrderedForPrinting : list of str
            List of material names ordered for printing.
        """
        super().write(folderPath, materialNamesOrderedForPrinting)

        if 'ICRU' in self._nuclear_data:
            with open(os.path.join(folderPath, self.name, 'ICRU_Nuclear_elastic.dat'), 'w',encoding="utf-8") as f:
                f.write(self._nuclearElasticData)

            with open(os.path.join(folderPath, self.name, 'ICRU_Nuclear_inelastic.dat'), 'w',encoding="utf-8") as f:
                f.write(self._nuclearInelasticData)

            with open(os.path.join(folderPath, self.name, 'ICRU_PromptGamma.dat'), 'w') as f:
                f.write(self._promptGamma)
