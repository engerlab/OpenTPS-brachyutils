from math import log, pi

import numpy as np

from opentps.core.data.CTCalibrations.MCsquareCalibration._G4StopPow import G4StopPow, SP
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareElement import MCsquareElement
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMaterial import MCsquareMaterial
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMolecule import MCsquareMolecule
from opentps.core.data.CTCalibrations.RayStationCalibration._X0 import X0


class RayStationMaterial:
    """
    Class to represent a material in RayStation.

    Attributes
    ----------
    density : float
        Density of the material in g/cm3.
    electronDensity : float
        Electron density of the material in cm-3.
    radiationLength : float
        Radiation length of the material in cm.
    I : float !! USED ONLY AT INITIALIZATION !!
        Mean excitation energy of the material in eV.
    """

    _eV = 1.602176634e-19  # J
    _MeV = 1.0e6 * _eV
    _c = 299792458.0  # m / s
    _m_e = 0.51998910 * _MeV / (_c * _c)  # electron mass
    _m_p = 938.272046 * _MeV / (_c * _c)  # proton mass
    _u = 931.49410242 * _MeV / (_c * _c)  # atomic mass unit
    _e = 1.602176634e-19  # Elementary charge
    _NA = 6.02214076e23
    _re = 2.8179403227e-15  # m
    _I_water = 68.0 * _eV
    _Z_water = np.array([1.0, 8.0])
    _A_water = np.array([1.01, 16])
    _w_water = np.array([2.02 / 18.02, 16.0 / 18.02])
    _density_water = 1.0

    def __init__(self, density=None, I=None):
        self._As = []
        if density<=0:
            self._density = 0.0001
        else:
            self._density = density
        self._I = I
        self._weights = []
        self._Zs = []

    def __str__(self):
        return self.rayStationFormatted()

    def rayStationFormatted(self):
        """
        Returns a string with the material formatted as in RayStation.

        Returns
        -------
        str
            String with the material formatted as in RayStation.
        """
        s = 'Density = ' + str(self._density) + ' gr/cm3 nElements = ' + str(len(self._weights)) + ' I = ' + str(self._I) + ' eV\n'
        for i, _ in enumerate(self._weights):
            s = s + str(i) + ' ' + str(self._Zs[i]) + ' ' + str(self._As[i]) + ' ' + str(self._weights[i]) + '\n'

        return s

    def appendElement(self, weight, A, Z):
        """
        Appends an element to the material.

        Parameters
        ----------
        weight : float
            Weight of the element in the material in g/cm3.
        A : float
            Atomic weight of the element.
        Z : int
            Atomic number of the element.
        """
        self._weights.append(weight)
        self._As.append(A)
        self._Zs.append(Z)

    @property
    def density(self):
        return self._density

    @property
    def electronDensity(self):
        w = np.array(self._weights)
        A = np.array(self._As)
        Z = np.array(self._Zs)

        a1 = sum(w * Z / A)

        return a1*self._density*self._NA

    @property
    def radiationLength(self):
        X = np.array(X0)
        w = np.array(self._weights)
        Z = np.array(self._Zs, dtype=int)

        X = X[Z-1]
        return 1.0/np.sum(w/X)

    def getRSP(self, energy):
        """
        Returns the relative stopping power of the material at the given energy.

        Parameters
        ----------
        energy : float
            Energy of the particle in MeV.

        Returns
        -------
        float
            Relative stopping power of the material at the given energy.
        """
        #Should we rather raise an error?
        if energy<=0:
            return 0

        SPR = self._density * self.getSP(energy) / self._waterSP(energy)
        return SPR

    def _waterSP(self, energy):
        E = energy * self._MeV
        a1 = sum(self._w_water * self._Z_water / self._A_water)
        a2 = log(2.0 * self._m_e * self._c * self._c / self._I_water)
        beta_2 = 1.0 - np.power(1 + E / (self._m_p * self._c * self._c), -2)
        S_water_Jm2g_RS = 4 * pi * self._NA * self._re * self._re * self._m_e * self._c * self._c * a1 * (
                    a2 - log(1.0 / beta_2 - 1.0) - beta_2) / beta_2

        return S_water_Jm2g_RS

    def getSP(self, energy):
        """
        Returns the stopping power of the material at the given energy.

        Parameters
        ----------
        energy : float
            Energy of the particle in MeV.

        Returns
        -------
        float
            Stopping power of the material at the given energy.
        """
        E = energy * self._MeV
        I = self._I * self._eV

        w = np.array(self._weights)
        A = np.array(self._As)
        Z = np.array(self._Zs)

        a1 = sum(w * Z / A)
        a2 = log(2.0 * self._m_e * self._c * self._c / I)
        beta_2 = 1.0 - np.power(1 + E / (self._m_p * self._c * self._c), -2)

        S = 4.0 * pi * self._NA * self._re * self._re * self._m_e * self._c * self._c * a1 * (a2 - log(1.0 / beta_2 - 1.0) - beta_2) / beta_2
        return S

    def toMCSquareMaterial(self, materialsPath='default'):
        """
        Converts the material to a MCsquareMaterial.

        Parameters
        ----------
        materialsPath : str (default='default')
            Path to the materials folder of MCsquare.

        Returns
        -------
        MCsquareMolecule
            MCsquareMolecule corresponding to the material.
        """
        materialNumbers = MCsquareMaterial.getMaterialNumbers(materialsPath)

        MCSquareElements = []
        MCSquareAWs = []
        waterSP = None
        for materialNumber in materialNumbers:
            try:
                element = MCsquareElement.load(materialNumber, materialsPath)
                MCSquareElements.append(element)
                MCSquareAWs.append(element.atomicWeight)
            except BaseException as err:
                pass

            if not(waterSP is None):
                continue

            try:
                molecule = MCsquareMolecule.load(materialNumber, materialsPath)
                if molecule.name == 'Water':
                    waterSP = molecule.sp
            except:
                pass

        MCSquareAWs = np.array(MCSquareAWs)

        selectedElement = []
        weigths = []
        for i, A in enumerate(self._As):
            closestElement = MCSquareElements[(np.abs(MCSquareAWs - A)).argmin()]

            if closestElement in selectedElement:
                weigths[selectedElement==closestElement] += self._weights[i]*100
            else:
                weigths.append(self._weights[i]*100)
                selectedElement.append(closestElement)

        waterEnergies, waterSPs = waterSP.toList()

        SPs = []
        for i, energy in enumerate(waterEnergies):
            SPs.append(SP(energy, self.getRSP(energy)*waterSPs[i]/(self._density+1e-4))) #1e-4 not to devide by 0

        sp = G4StopPow(SPs)

        newName = str(self._density).replace('.', '_')

        return MCsquareMolecule(density=self._density, electronDensity=self.electronDensity, name=newName,
                                number=0, sp=sp, radiationLength=self.radiationLength,
                                MCsquareElements=selectedElement, weights=weigths)

