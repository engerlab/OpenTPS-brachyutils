
__all__ = ['PiecewiseHU2Density']


import re

import numpy as np
from scipy.interpolate import interpolate


class PiecewiseHU2Density:
    """
    Class for converting HU to mass density and vice versa. The conversion is done using linear interpolation.

    Attributes
    ----------
    !! USED ONLY AT INITIALIZATION !!
    fromFile : str
        Path to the file containing the HU to mass density conversion table.
    piecewiseTable : tuple
        Tuple containing the HU to mass density conversion table.
    """
    _DENSITY_EPS = 0.0001
    def __init__(self, piecewiseTable=([], []), fromFile=None):
        self.__hu = piecewiseTable[0]
        self.__densities = piecewiseTable[1]

        if not (fromFile is None):
            self._initializeFromFile(fromFile)

    # despite __ in __str__ this is not considered 'private' by python which is more than logical
    # If we subclass this class, __str__ is overloaded and when we call __str__ from this class we would actually call __str__ from subclass
    def __str__(self):
        return self.__str()

    def __str(self):
        return self.writeableTable()

    @classmethod
    def fromFile(cls, huDensityFile):
        """
        Create a PiecewiseHU2Density object from a file.

        Parameters
        ----------
        huDensityFile : str
            Path to the file containing the HU to mass density conversion table.

        Returns
        -------
        PiecewiseHU2Density
            The PiecewiseHU2Density object.
        """
        newObj = cls()
        newObj._initializeFromFile(huDensityFile)

        return newObj

    def _initializeFromFile(self, huDensityFile):
        self.__load(huDensityFile)
    
    def writeHeader(self):
        """
        Return header of HU to density conversion table
        """
        s =  "# ===================\n"
        s += "# HU	density g/cm3\n"
        s += "# ===================\n\n"
        return s

    def writeableTable(self):
        """
        Returns a string containing the HU to mass density conversion table.

        Returns
        -------
        str
            The HU to mass density conversion table.
        """
        s = ''
        for i, hu in enumerate(self.__hu):
            density = self.__densities[i]

            if density<self._DENSITY_EPS:
                density = self._DENSITY_EPS

            s += str(hu) + ' ' + str(density) + '\n'

        return s

    def addEntry(self, hu:float, density:float):
        """
        Add an entry to the HU to mass density conversion table.

        Parameters
        ----------
        hu : float
            The Housnfield unit value.
        density : float
            The mass density value.
        """
        self.__hu = np.append(self.__hu, hu)
        self.__densities = np.append(self.__densities, density)

        self.__hu = np.array(self.__hu)
        self.__densities = np.array(self.__densities)

        ind = np.argsort(self.__hu)

        self.__hu = self.__hu[ind]
        self.__densities = self.__densities[ind]

    def write(self, scannerFile):
        """
        Write the HU to mass density conversion table to a file.

        Parameters
        ----------
        scannerFile : str
            Path to the file to write the HU to mass density conversion table to.
        """
        with open(scannerFile, 'w') as f:
            f.write(self.writeHeader())
            f.write(self.writeableTable())

    def convertMassDensity2HU(self, densities):
        """
        Convert mass density to Housnfield unit.

        Parameters
        ----------
        densities : float or array_like
            The mass density value(s).

        Returns
        -------
        float or array_like
            The Housnfield unit value(s).
        """
        #Ensure density is monotonically increasing
        HU_ref = np.arange(self.__hu[0], self.__hu[-1], 1)
        density_ref = self.convertHU2MassDensity(HU_ref)

        density_ref, ind = np.unique(density_ref, return_index=True)
        HU_ref = HU_ref[ind]

        while not np.all(np.diff(density_ref) >= 0):
            d_diff = np.concatenate((np.array([1.0]), np.diff(density_ref)))

            density_ref = density_ref[d_diff > 0]
            HU_ref = HU_ref[d_diff > 0]

            density_ref, ind = np.unique(density_ref, return_index=True)
            HU_ref = HU_ref[ind]

        hu = interpolate.interp1d(density_ref, HU_ref, kind='linear', fill_value='extrapolate')

        # If densities as 0, interpolation returns nan but we must return 0
        res = np.array(hu(densities))
        res[np.isnan(res)] = 0.

        if res.ndim==1:
            res = res[0]

        return res

    def convertHU2MassDensity(self, hu):
        """
        Convert Housnfield unit to mass density.

        Parameters
        ----------
        hu : float or array_like
            The Housnfield unit value(s).

        Returns
        -------
        float or array_like
            The mass density value(s).
        """
        f = interpolate.interp1d(self.__hu, self.__densities, kind='linear', fill_value='extrapolate')

        density = f(hu)
        density[density<0] = 0

        return density

    def getPiecewiseHU2MassDensityConversion(self):
        """
        Get the HU to mass density conversion table.

        Returns
        -------
        tuple
            The HU to mass density conversion table.
        """
        return (self.__hu, self.__densities)

    def load(self, scannerFile):
        """
        Load the HU to mass density conversion table from a file.

        Parameters
        ----------
        scannerFile : str
            Path to the file containing the HU to mass density conversion table.
        """
        return self.__load(scannerFile)

    def __load(self, scannerFile):
        # Read scanner file
        hu = []
        density = []
        foundHU_to_Density = False

        with open(scannerFile, "r") as file:
            for line in file:
                #'HU_to_Density' for Reggui format and 'density' for MCsquare format
                if re.search(r'HU_to_Density', line) or re.search(r'density', line):
                    foundHU_to_Density = True
                    continue
                if foundHU_to_Density and re.search(r'HU', line):
                    break
                elif foundHU_to_Density:
                    lineSplit = line.split()                    
                    if len(lineSplit)<1:
                        continue
                    if lineSplit[0]=='#':
                        continue

                    hu.append(float(lineSplit[0]))
                    density.append(float(lineSplit[1]))

        self.setPiecewiseHU2MassDensityConversion((hu, density))

    def setPiecewiseHU2MassDensityConversion(self, piecewiseTable):
        """
        Set the HU to mass density conversion table.
        """
        self.__hu = piecewiseTable[0]
        self.__densities = piecewiseTable[1]


