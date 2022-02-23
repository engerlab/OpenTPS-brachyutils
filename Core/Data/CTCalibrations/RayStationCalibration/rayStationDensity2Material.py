import re

import numpy as np
from scipy.interpolate import interpolate

from Core.Data.CTCalibrations.RayStationCalibration.rayStationMaterial import RayStationMaterial


class RayStationDensity2Material:
    def __init__(self, densities=None, materials=None, fromFile=None):
        self._densities = None
        self._materials = materials

        if not densities is None:
            self._densities = np.array(densities)

        if not (fromFile is None):
            self._load(fromFile)

    def __getitem__(self, density):
        densityIsScalar = not(density is list)

        if densityIsScalar:
            return self._getClosestMaterial(density)
        else:
            # TODO: in Matlab, I would use a repmat would in be faster in numpy as well?
            return list(map(self._getClosestMaterial, density))

    def _getClosestMaterial(self, density):
        materialIndex = self._getIndexOfClosestDensity(density)
        return self._materials[materialIndex]

    def _getIndexOfClosestDensity(self, density):
        return self._materials[(np.abs(self._densities - density)).argmin()]

    def __str__(self):
        return self.rayStationFormatted

    def rayStationFormatted(self):
        s  = ''
        for i, material in enumerate(self._materials):
            s = s + str(i) + ' ' + material.rayStationFormatted() + '\n'

        return s

    def convertMassDensity2RSP(self, density, energy=100):
        densityIsScalar = not (density is list)

        if densityIsScalar:
            return density*self[density].getRSP(energy)/(self[density].getDensity()+1e-4) #1e-4 to avoid dividing by 0
        else:
            return list(map(lambda d: self.convertMassDensity2RSP(d, energy=energy), density))

    def convertRSP2MassDensity(self, rsp, energy=100):
        density_ref, rsp_ref = self._getBijectiveMassDensity2RSP(energy=energy)

        density = interpolate.interp1d(rsp_ref, density_ref, kind='linear', fill_value='extrapolate')

        return density(rsp)

    def _getBijectiveMassDensity2RSP(self, densityMin=0., densityMax=5., step=0.01, energy=100):
        density_ref = np.arange(densityMin, densityMax, step)
        rsp_ref = self.convertMassDensity2RSP(density_ref, energy)
        rsp_ref = np.array(rsp_ref)

        while not np.all(np.diff(rsp_ref) >= 0):
            rsp_diff = np.concatenate((np.array([1.0]), np.diff(rsp_ref)))

            rsp_ref = rsp_ref[rsp_diff > 0]
            density_ref = density_ref[rsp_diff > 0]

            rsp_ref, ind = np.unique(rsp_ref, return_index=True)
            density_ref = density_ref[ind]

        return (density_ref, rsp_ref)


    def getDensities(self):
        return np.array(self._densities)

    def getMaterials(self):
        return self._materials

    def _load(self, materialFile):
        # Read material file
        densities = []
        materials = []

        foundMaterial = False
        with open(materialFile, 'r') as file:
            for line in file:
                if len(line) == 0:
                    foundMaterial = False
                    continue

                if re.search(r'Density', line):
                    foundMaterial = True
                    lineSplit = line.split()
                    material = RayStationMaterial(density=float(lineSplit[3]), I=float(lineSplit[10]))
                    densities.append(float(lineSplit[3]))
                    materials.append(material)
                    continue

                if foundMaterial:
                    lineSplit = line.split()
                    if len(lineSplit) < 4:
                        foundMaterial = False
                        continue
                    material.appendElement(float(lineSplit[3]), float(lineSplit[2]), float(lineSplit[1]))

        self.setDensities(densities)
        self.setMaterials(materials)

    def setDensities(self, densities):
        self._densities = np.array(densities)

    def setMaterials(self, materials):
        self._materials = materials
