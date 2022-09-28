
__all__ = ['PiecewiseHU2Density']


import re

import numpy as np
from scipy.interpolate import interpolate


class PiecewiseHU2Density:
    _DENSITY_EPS = 0.0001

    def __init__(self, piecewiseTable=(None, None), fromFile=None):
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
        newObj = cls()
        newObj._initializeFromFile(huDensityFile)

        return newObj

    def _initializeFromFile(self, huDensityFile):
        self.__load(huDensityFile)

    def writeableTable(self):
        s = ''
        for i, hu in enumerate(self.__hu):
            density = self.__densities[i]

            if density<self._DENSITY_EPS:
                density = self._DENSITY_EPS

            s += str(hu) + ' ' + str(density) + '\n'

        return s

    def addEntry(self, hu:float, density:float):
        self.__hu = np.append(self.__hu, hu)
        self.__densities = np.append(self.__densities, density)

        self.__hu = np.array(self.__hu)
        self.__materials = np.array(self.__densities)

        ind = np.argsort(self.__hu)

        self.__hu = self.__hu[ind]
        self.__materials = self.__materials[ind]

    def write(self, scannerFile):
        with open(scannerFile, 'w') as f:
            f.write(self.writeableTable())

    def convertMassDensity2HU(self, densities):
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
        f = interpolate.interp1d(self.__hu, self.__densities, kind='linear', fill_value='extrapolate')

        density = f(hu)
        density[density<0] = 0

        return density

    def getPiecewiseHU2MassDensityConversion(self):
        return (self.__hu, self.__densities)

    def load(self, scannerFile):
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

                    if lineSplit[0]=='#':
                        continue

                    hu.append(float(lineSplit[0]))
                    density.append(float(lineSplit[1]))

        self.setPiecewiseHU2MassDensityConversion((hu, density))

    def setPiecewiseHU2MassDensityConversion(self, piecewiseTable):
        self.__hu = piecewiseTable[0]
        self.__densities = piecewiseTable[1]


