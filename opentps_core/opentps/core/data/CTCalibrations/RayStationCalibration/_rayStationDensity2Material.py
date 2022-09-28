import re
from typing import Sequence, Union

import numpy as np
from numpy.matlib import repmat
from scipy.interpolate import interpolate

from opentps.core.data.CTCalibrations.RayStationCalibration._rayStationMaterial import RayStationMaterial


class RayStationDensity2Material:
    def __init__(self, densities=None, materials=None, fromFile=None):
        self._densities = None
        self._materials = materials

        if not densities is None:
            self._densities = np.array(densities)

        if not (fromFile is None):
            self._load(fromFile)

    def __getitem__(self, density:Union[float, np.ndarray]) -> Union[RayStationMaterial, Sequence[RayStationMaterial]]:
        densityIsScalar = not isinstance(density, np.ndarray)

        if densityIsScalar:
            return self._getClosestMaterial(density)
        else:
            return np.vectorize(self._getClosestMaterial)(density)

    def _getClosestMaterial(self, density:float) -> RayStationMaterial:
        materialIndex = self._getIndexOfClosestDensity(density)
        return self._materials[materialIndex]

    def _getIndexOfClosestDensity(self, density:float) -> int:
        return (np.abs(self._densities - density)).argmin()

    def __str__(self):
        return self.rayStationFormatted

    def rayStationFormatted(self)->str:
        s  = ''
        for i, material in enumerate(self._materials):
            s = s + str(i) + ' ' + material.rayStationFormatted() + '\n'

        return s

    def convertMassDensity2RSP(self, density:Union[float, np.ndarray], energy=100):
        densityIsScalar = not isinstance(density, np.ndarray)

        if densityIsScalar:
            material = self[density]
            return density*material.getRSP(energy)/(material.density+1e-4) #1e-4 to avoid dividing by 0
        else:
            if len(density.shape)==2:
                return self._convert2DMassDensity2RSP(density, energy=energy)
            elif len(density.shape)==3:
                rsps = np.zeros(density.shape)
                for i in range(density.shape[2]):
                    rsps[:, :, i]  = self._convert2DMassDensity2RSP(density[:, :, i], energy=energy)
                return rsps
            else:
                return np.vectorize(lambda d: self.convertMassDensity2RSP(d, energy=energy))(density)

    def _convert2DMassDensity2RSP(self, density:np.ndarray, energy=100) -> np.ndarray:
        densityShape = density.shape

        density = density.flatten()
        densityLen = max(density.shape)

        densityRefLen = max(self._densities.shape)

        referenceDensities = repmat(self._densities.reshape(densityRefLen, 1), 1, densityLen)
        queryDensities = repmat(density.reshape(1, densityLen), densityRefLen, 1)

        indexOfClosestDensity = (np.abs(referenceDensities - queryDensities)).argmin(axis = 0)

        materialsDensity = np.vectorize(lambda m: m.density)(self._materials)
        materialsRSP = np.vectorize(lambda m: m.getRSP(energy=energy))(self._materials)

        materialsDensity = materialsDensity[indexOfClosestDensity]
        materialsRSP = materialsRSP[indexOfClosestDensity]

        density = np.reshape(density, densityShape)
        materialsDensity = np.reshape(materialsDensity, densityShape)
        materialsRSP = np.reshape(materialsRSP, densityShape)

        return density * materialsRSP / (materialsDensity + 1e-4)  # 1e-4 to avoid dividing by 0


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
