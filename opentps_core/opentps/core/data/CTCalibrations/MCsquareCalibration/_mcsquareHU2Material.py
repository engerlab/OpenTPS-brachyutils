import os
from distutils.dir_util import copy_tree
from glob import glob
from typing import Sequence, Union

import numpy as np
from numpy.matlib import repmat

from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMaterial import MCsquareMaterial
from opentps.core.data.CTCalibrations.MCsquareCalibration._mcsquareMolecule import MCsquareMolecule

import opentps.core.processing.doseCalculation.MCsquare as MCsquareModule


class MCsquareHU2Material:
    def __init__(self, piecewiseTable=(None, None), fromFile=(None, 'default')):
        self.__hu = piecewiseTable[0]
        self.__materials = piecewiseTable[1]

        if not (fromFile[0] is None):
            self._initializeFromFiles(fromFile[0], materialsPath=fromFile[1])

    def __str__(self):
        return self.mcsquareFormatted()

    @classmethod
    def fromFiles(cls, huMaterialFile, materialsPath='default'):
        newObj = cls()
        newObj._initializeFromFiles(huMaterialFile, materialsPath)

        return newObj

    def _initializeFromFiles(self, huMaterialFile, materialsPath='default'):
        self.__load(huMaterialFile, materialsPath=materialsPath)

    def addEntry(self, hu:float, material:MCsquareMolecule):
        self.__hu = np.append(self.__hu, hu)
        self.__materials = np.append(self.__materials, material)

        self.__hu = np.array(self.__hu)
        self.__materials = np.array(self.__materials)

        ind = np.argsort(self.__hu)

        self.__hu = self.__hu[ind]
        self.__materials = self.__materials[ind]

    def mcsquareFormatted(self):
        mats = self.allMaterialsAndElements()
        matNames = [mat.name for mat in mats]

        s = ''
        for i, hu in enumerate(self.__hu):
            s += 'HU: ' + str(hu) + '\n'
            s += self.__materials[i].mcsquareFormatted(matNames) + '\n'

        return s

    def convertHU2SP(self, hu:Union[float, np.ndarray], energy:float = 100.) ->  Union[float, np.ndarray]:
        huIsScalar = not isinstance(hu, np.ndarray)

        if huIsScalar:
            return self._convert2DHU2SP(np.array([hu]), energy=energy)[0]
        else:
            if len(hu.shape) == 2:
                return self._convert2DHU2SP(hu, energy=energy)
            elif len(hu.shape) == 3:
                rsps = np.zeros(hu.shape)
                for i in range(hu.shape[2]):
                    rsps[:, :, i] = self._convert2DHU2SP(hu[:, :, i], energy=energy)
                return rsps
            else:
                return np.vectorize(lambda h: self.convertHU2SP(h, energy=energy))(hu)

    def _convert2DHU2SP(self, hu:np.ndarray, energy:float=100.) -> np.ndarray:
        huShape = hu.shape

        hu = hu.flatten()
        huLen = max(hu.shape)

        spRef = np.array([material.stoppingPower(energy) for material in self.__materials])
        huRef = np.array(self.__hu)
        huRefLen = max(spRef.shape)

        referenceHUs = repmat(huRef.reshape(huRefLen, 1), 1, huLen)
        queryHUs = repmat(hu.reshape(1, huLen), huRefLen, 1)

        diff = referenceHUs - queryHUs
        diff[diff>0] = -9999
        indexOfClosestSP = (np.abs(diff)).argmin(axis=0)

        sp = spRef[indexOfClosestSP]

        return np.reshape(sp, huShape)

    def convertSP2HU(self, sp:Union[float, np.ndarray], energy:float = 100.) ->  Union[float, np.ndarray]:
        spIsScalar = not isinstance(sp, np.ndarray)

        if spIsScalar:
            return self._convert2DSP2HU(np.array([sp]), energy=energy)[0]
        else:
            if len(sp.shape) == 2:
                return self._convert2DSP2HU(sp, energy=energy)
            elif len(sp.shape) == 3:
                rsps = np.zeros(sp.shape)
                for i in range(sp.shape[2]):
                    rsps[:, :, i] = self._convert2DSP2HU(sp[:, :, i], energy=energy)
                return rsps
            else:
                return np.vectorize(lambda s: self.convertHU2SP(s, energy=energy))(sp)

    def _convert2DSP2HU(self, sp:np.ndarray, energy:float=100.) -> np.ndarray:
        spShape = sp.shape

        sp = sp.flatten()
        spLen = max(sp.shape)

        spRef = np.array([material.stoppingPower(energy) for material in self.__materials])
        spRefLen = max(spRef.shape)

        referenceSPs = repmat(spRef.reshape(spRefLen, 1), 1, spLen)
        querySPs = repmat(sp.reshape(1, spLen), spRefLen, 1)

        indexOfClosestSP = (np.abs(referenceSPs - querySPs)).argmin(axis=0)

        refHUs = np.array(self.__hu)
        hu = refHUs[indexOfClosestSP]

        return np.reshape(hu, spShape)

    def __load(self, materialFile, materialsPath='default'):
        self.__hu = []
        self.__materials = []

        with open(materialFile, "r") as file:
            for line in file:
                lineSplit = line.split()
                if len(lineSplit)<=0:
                    continue

                if lineSplit[0] == '#':
                    continue

                # else
                if len(lineSplit) > 1:
                    self.__hu.append(float(lineSplit[0]))

                    material = MCsquareMolecule.load(int(lineSplit[1]), materialsPath)
                    self.__materials.append(material)

    def write(self, folderPath, huMaterialFile):
        self._writeHU2MaterialFile(huMaterialFile)
        self._copyDefaultMaterials(folderPath)
        self._writeMaterials(folderPath)
        self._writeMCsquareList(os.path.join(folderPath, 'list.dat'))

    def _writeHU2MaterialFile(self, huMaterialFile):
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()

        with open(huMaterialFile, 'w') as f:
            for i, hu in enumerate(self.__hu):
                s = str(hu) + ' ' + str(materialsOrderedForPrinting.index(self.__materials[i])+1) + '\n'
                f.write(s)

    def _writeMaterials(self, folderPath):
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()
        matNames = [mat.name for mat in materialsOrderedForPrinting]

        for material in self.allMaterialsAndElements():
            material.write(folderPath, matNames)

    def _copyDefaultMaterials(self, folderPath):
        materialsPath = os.path.join(str(MCsquareModule.__path__[0]), 'Materials')

        for folder in glob(materialsPath + os.path.sep + '*' + os.path.sep):
            y = folder.split(os.path.sep)
            last_folder = y[-1]
            if last_folder=='':
                last_folder = y[-2]

            targetFolder = os.path.join(folderPath, os.path.basename(last_folder))
            os.makedirs(targetFolder, exist_ok=True)
            copy_tree(folder, targetFolder)

    def _writeMCsquareList(self, listFile):
        materialsOrderedForPrinting = self.materialsOrderedForPrinting()

        with open(listFile, 'w') as f:
            for i, mat in enumerate(materialsOrderedForPrinting):
                f.write(str(i+1) + ' ' + mat.name + '\n')

    def materialsOrderedForPrinting(self):
        materials = self.allMaterialsAndElements()
        defaultMats = MCsquareMaterial.getMaterialList('default')

        orderMaterials = []
        for mat in defaultMats:
            newMat = MCsquareMaterial()
            newMat.name = mat["name"]
            orderMaterials.append(newMat)

        for material in materials:
            orderMaterials.append(material)

        return orderMaterials

    def allMaterialsAndElements(self):
        materials = []
        for material in self.__materials:
            materials.append(material)

            for element in material.MCsquareElements:
                materials.append(element)

        return self._sortMaterialsandElements(materials)

    def _sortMaterialsandElements(self, materials:Sequence[MCsquareMaterial]) -> Sequence[MCsquareMaterial]:
        uniqueMaterials = []

        materialNames = [material.name for material in materials]
        _, ind = np.unique(materialNames, return_index=True)

        for i in ind:
            uniqueMaterials.append(materials[i])

        uniqueMaterials.sort(key=lambda e:e.number)

        return uniqueMaterials